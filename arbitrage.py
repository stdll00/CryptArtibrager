import api.model
import api.bitbank
import api.bitpoint
import api.quoinex
import get_all_balance
import time
import itertools
from requests.packages.urllib3.exceptions import ProtocolError
import datetime
from socket import error as SocketError
from collections import defaultdict, deque

bitbank = api.bitbank.BitBank()
bitpoint = api.bitpoint.Bitpoint()
quoinex = api.quoinex.Quoinex()

_debug = False
_version = "1.06"

# Threshold
BTC_IGNORE_AMOUNT = 0.005
LOOP_COUNT = 3000
print("BTC thredsholds")
if _debug:
    print("DEBUG MODE")
print("version :", _version)
print("tsucho:")
get_all_balance.output(bitpoint, bitbank, quoinex)


class Arbitrager():
    EXEC_OFFSET = {'BTC': 1200}
    diff_log = defaultdict(lambda: defaultdict(lambda: deque(maxlen=LOOP_COUNT)))

    def __init__(self, crypt_exchanges,callback_when_buy=None):
        self.crypt_exchanges = crypt_exchanges
        self.start_balance = self.total_balance()
        self.callback_when_execute = callback_when_buy

    def __len__(self):
        return len(self.crypt_exchanges)

    def api_check(self):
        self.update_price()
        min_ask = min([exchange.last_ask for exchange in self.crypt_exchanges])
        for exchange in self.crypt_exchanges:
            assert isinstance(exchange, api.model.CryptExchange)
            result_amount = exchange.take_order('BTC', min_ask * 0.95, 0.001, side='buy')
            if result_amount:
                return 1

    def total_balance(self):
        total_balance = defaultdict(float)
        for exchange in self.crypt_exchanges:
            for key in exchange.balance:
                total_balance[key] += exchange.balance[key]
        return total_balance

    def balance_diff(self, other_total_balance):
        assert isinstance(other_total_balance, dict)
        total_balance = self.total_balance()

        result = defaultdict(float)
        for key in other_total_balance:
            if total_balance[key] - other_total_balance[key] == 0:
                continue
            result[key] = total_balance[key] - other_total_balance[key]
        return dict(result), str(dict(result))

    def update_price(self, _debug=False):
        for exchange in self.crypt_exchanges:
            assert isinstance(exchange, api.model.CryptExchange)
            if _debug:
                time_start = time.time()
            exchange.get_price()
            if _debug:
                print(exchange.NAME, time.time() - time_start, exchange.last_bid, exchange.last_ask,
                      exchange.last_ask > exchange.last_bid)

    def update_balance(self):
        for exchange in self.crypt_exchanges:
            # assert isinstance(exchange, api.model.CryptExchange)
            exchange.get_balance()

    @staticmethod
    def limit_amount(amount):
        return int(amount * 1000) / 1000

    def run(self, currency='BTC'):
        message = ""
        try:
            self.update_price()
        except (ConnectionResetError, TypeError, ConnectionError, ProtocolError, SocketError):
            return 1, "Error"

        for buy_exchange, sell_exchange in itertools.permutations(self.crypt_exchanges, 2):

            assert isinstance(buy_exchange, api.model.CryptExchange) and \
                   isinstance(sell_exchange, api.model.CryptExchange)
            diff_threshold = sell_exchange.BID_OFFSET[currency] + buy_exchange.ASK_OFFSET[currency] + self.EXEC_OFFSET[
                currency]
            diff = int(sell_exchange.last_bid - buy_exchange.last_ask)
            amount_executable = self.limit_amount(
                max(
                    min(buy_exchange.amount_can_market_buy(),
                        sell_exchange.amount_can_sell()),
                    min(buy_exchange.amount_can_buy(),
                        sell_exchange.amount_can_market_sell())
                    , 0)
            )
            self.diff_log[currency][(sell_exchange.NAME, buy_exchange.NAME)].append(diff)
            # TODO Check timestamp of price

            message += ("sell:" + sell_exchange.NAME.ljust(8) + "  buy:" + buy_exchange.NAME.ljust(8) + "  ")
            message += " ".join(map(lambda x: str(x).rjust(5), (
                diff_threshold, max(self.diff_log[currency][(sell_exchange.NAME, buy_exchange.NAME)]),
                amount_executable,
                int(diff), " "))) + "\n"

            if diff >= diff_threshold:
                taker_side = "buy" if buy_exchange.PRIORITY < sell_exchange.PRIORITY else "sell"
                if taker_side == "sell":
                    amount = min(buy_exchange.amount_can_market_buy(), sell_exchange.amount_can_sell())
                else:
                    amount = min(buy_exchange.amount_can_buy(), sell_exchange.amount_can_market_sell())
            elif currency == "BTC" and diff > 500 and buy_exchange.balance["BTC"] < -1.0 and sell_exchange.balance["BTC"] > 1:
                taker_side = "buy" if buy_exchange.PRIORITY < sell_exchange.PRIORITY else "sell"
                if taker_side == "sell":
                    amount = min(0.5, buy_exchange.amount_can_market_buy(), sell_exchange.amount_can_sell())
                else:
                    amount = min(0.5, buy_exchange.amount_can_buy(), sell_exchange.amount_can_market_sell())
            elif currency == "BTC" and diff > 300 and 0.4 > sell_exchange.balance["BTC"] > -3.0 and 0 < \
                    buy_exchange.balance["BTC"] < 3:
                taker_side = "buy" if buy_exchange.PRIORITY < sell_exchange.PRIORITY else "sell"
                if taker_side == "sell":
                    amount = min(0.6, buy_exchange.amount_can_market_buy(), sell_exchange.amount_can_sell())
                else:
                    amount = min(0.6, buy_exchange.amount_can_buy(), sell_exchange.amount_can_market_sell())

            else:
                continue
            if amount < BTC_IGNORE_AMOUNT:
                continue
            amount = self.limit_amount(amount)
            self.execute(buy_exchange, sell_exchange, amount=amount, taker_side=taker_side)
            [print() for _ in range(len(self) * (len(self) - 1) + 1)]
            return 0, '\n' * 6
        return 0, message

    def execute(self, buy_exchange, sell_exchange, amount, taker_side, currency="BTC"):
        assert isinstance(buy_exchange, api.model.CryptExchange) and \
               isinstance(sell_exchange, api.model.CryptExchange)

        message = "first:" + taker_side + " init_amount:" + str(
            amount) + "  buy:" + buy_exchange.NAME + " sell:" + sell_exchange.NAME + \
                  "  price:" + str(int(buy_exchange.last_ask)) + \
                  "  diff: " + str(int(sell_exchange.last_bid - buy_exchange.last_ask))

        if amount < BTC_IGNORE_AMOUNT:
            return
        print(datetime.datetime.today())
        old_balance = self.total_balance()
        [print() for _ in range(len(self) * (len(self) - 1) + 1)]
        print(message)

        if taker_side == "buy":
            result_amount = buy_exchange.take_order("BTC", price=buy_exchange.last_ask, amount=amount, side="buy")
            if float(result_amount) >= sell_exchange.MIN_BTC_TRADE_AMOUNT:
                sell_exchange.send_order("BTC", price=sell_exchange.last_bid, amount=float(result_amount), side='sell',
                                         order_type='market')
            else:
                print("amount not enough")

        elif taker_side == "sell":
            result_amount = sell_exchange.take_order("BTC", price=sell_exchange.last_bid, amount=amount, side="sell")
            if float(result_amount) >= buy_exchange.MIN_BTC_TRADE_AMOUNT:
                buy_exchange.send_order("BTC", price=buy_exchange.last_ask, amount=float(result_amount), side='buy',
                                        order_type='market')
            else:
                print("amount not enough")
                return

        print()

        for i in range(40):
            time.sleep(5)
            self.update_balance()
            total_balance = self.total_balance()
            # トータルで見てポジションを持っていないことを確認する
            if self.start_balance[currency] * 0.92 - 0.01 < total_balance[currency] < self.start_balance[currency] * 1.06 + 0.01:
                print('balance checked')
                balance_diff, balance_diff_in_string = self.balance_diff(old_balance)
                print(balance_diff)
                estimate = int(result_amount * (sell_exchange.last_bid - buy_exchange.last_ask))
                self.callback_when_execute(
                    str(result_amount) + " " + message + '\n' + 'est:' + str(estimate) + '\n' + balance_diff_in_string)
                return
            print('balance invalid')
            print(total_balance)

        raise Exception

