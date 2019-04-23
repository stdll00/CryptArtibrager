import json
import os.path
import api.model
import python_bitbankcc
import time
from collections import defaultdict
from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
import threading

BASE_PATH = "https://api.bitbank.cc/v1"


class BitBank(api.model.CryptExchange):
    BTC_AMOUNT_MAX = 0.27
    AMOUNT_LIMIT = 0.4

    AMOUNT_LIMITS = defaultdict(float, {"BTC": 0.4, "XRP": 100, "ETH": 1})
    NAME = "BitBank"
    PRIORITY = 1.0
    balance = {}
    BID_OFFSET = {"BTC": 800}
    ASK_OFFSET = {"BTC": 800}

    def __init__(self, public=False):

        self.pub = python_bitbankcc.public()
        if not public:
            account = json.load(
                open(
                    os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        ".auth.json")
                )
            )["bitbank"]
            self.prv = python_bitbankcc.private(account["apikey"], account["secret"])
            self.get_balance()
        self.last_bid, self.last_ask = self.get_price()

    def get_balance(self):
        result = defaultdict(float)
        available = defaultdict(float)
        value = self.prv.get_asset()
        for item in (value)["assets"]:
            # print(item["asset"],item['free_amount'],item['locked_amount'])
            result[item['asset'].upper()] = float(item['free_amount']) + float(item['locked_amount'])
            available[item['asset'].upper()] = float(item['free_amount'])

        self.balance = result
        self.available = available
        return result

    def get_price(self, currency="BTC", amount_limit=AMOUNT_LIMIT, base_currency="jpy", ticker_data=None,
                  depthdata=None, timestamp=None, MESSAGE_IF_NOT_STREAM=False):
        assert currency in ["BTC", "ETH", "BCC", "MONA", "XRP"]
        last_price_obj = self.last_price[currency]
        assert isinstance(last_price_obj, api.model.CryptPrice)
        if last_price_obj.is_active():
            return last_price_obj.last_bid, last_price_obj.last_ask
        if MESSAGE_IF_NOT_STREAM:
            print("THIS IS NOT STREAM DATA")
        currency_pair = '{}_{}'.format(currency.lower(), base_currency.lower())

        def calc(_data):
            """
            板情報を使って計算する
            :param _data:
            :return:
            """
            amount_sum = 0
            for price, amount in _data:
                amount_sum += float(amount)
                if amount_limit < amount_sum:
                    return float(price)

        if amount_limit:
            data = self.pub.get_depth(currency_pair) if not depthdata else depthdata
            bid, ask = calc(data["bids"]), calc(data["asks"])
            if bid > ask:
                bid, ask = self.get_price(currency, amount_limit * 2, base_currency, depthdata=data)
        else:
            value = self.pub.get_ticker(
                currency_pair
            )
            bid, ask = float(value["buy"]), float(value["sell"])

        if not timestamp:
            timestamp = time.time()
        self.last_price[currency].update(bid, ask, last_modified=timestamp)
        # TODO No longer use
        if currency == "BTC":
            self.last_bid, self.last_ask = bid, ask

        return bid*0.9985, ask*1.0015

    def send_order(self, currency, price, amount, side, order_type='limit', base_currency="jpy"):
        assert side == 'buy' or side == 'sell'
        assert order_type in ['limit', 'market']
        currency_pair = currency.lower() + "_" + base_currency.lower()
        value = self.prv.order(
            currency_pair,  # ペア
            str(price),  # 価格
            str(amount),  # 注文枚数
            side,  # 注文サイド
            order_type  # 注文タイプ
        )
        print(json.dumps(value))
        if order_type == 'market':
            if side == "sell":
                self.available[currency] -= amount
            elif side == "buy":
                self.available["JPY"] -= amount * price * 1.1
        return (currency_pair, (value)["order_id"])

    def take_order(self, currency, price, amount, side, *args, **kwargs):
        def update_available(order_info):
            if side == 'buy':
                self.available["JPY"] -= float(order_info["average_price"]) * float(order_info["executed_amount"])
            elif side == 'sell':
                self.available[currency] += float(order_info["executed_amount"])

        if amount < 0.0001:
            print("Amount invalid")
            return 0
        currency_pair, order_no = self.send_order(currency, price, amount, side, order_type='limit')
        print(currency_pair, order_no)
        for i in range(9):
            time.sleep(0.8)
            order_info = self._get_order(currency_pair, order_no)
            if float(order_info["remaining_amount"]) == 0:
                update_available(order_info)
                return float(order_info["executed_amount"])
        try:
            self.cancel_order((currency_pair, order_no))
            print("order cancelled")
        except:
            print("order not cancelled")
            import traceback
            print(traceback.format_exc())

        order_info = self._get_order(currency_pair, order_no)
        update_available(order_info)
        return float(order_info["executed_amount"])

    def _get_trade_history(self, currency_pair, count):
        return self.prv.get_trade_history(
            currency_pair,  # ペア
            str(count)  # 取得する約定数
        )

    def _get_order(self, currency_pair, order_no):
        return self.prv.get_order(currency_pair, order_no)

    def _get_active_orders(self):
        return self.prv.get_active_orders()

    def cancel_order(self, order_value):
        value = self.prv.cancel_order(
            order_value[0],  # ペア
            order_value[1]  # 注文ID
        )
        print(value)
        for cancel_timing in [5, 10, 30, 100, 200, 300, 400]:
            threading.Timer(cancel_timing, self.prv.cancel_order, args=(order_value[0], order_value[1])).start()
            print("cancel_timer start")
        return value
        # print(json.dumps(value))

    def check_triangle_trade(self, currency):
        """
        JPY->BTC BTC->BCH BCH->JPY  など取引所内で儲かるかを確認する
        :param currency:
        :return:
        """
        # for mona and bcc
        btc_bit, btc_ask = self.get_price("BTC")
        btc_base_bit, btc_base_ask = self.get_price(currency, base_currency="btc")
        jpy_base_bit, jpy_base_ask = self.get_price(currency, base_currency="jpy")

        return (jpy_base_bit - btc_ask * btc_base_ask) / jpy_base_bit, \
               (btc_bit * btc_base_bit - jpy_base_ask) / jpy_base_bit

    def _stream(self, currency_list):
        SubscribeKey = "sub-c-e12e9174-dd60-11e6-806b-02ee2ddab7fe"
        pnconfig = PNConfiguration()
        pnconfig.daemon = True
        pnconfig.subscribe_key = SubscribeKey

        class MySubscribeCallback(SubscribeCallback):
            def __init__(self, currency, exchange_instance):
                super(MySubscribeCallback, self).__init__()
                self.currency = currency
                assert isinstance(exchange_instance, BitBank)
                self.excahgne_instance = exchange_instance

            def message(self, pubnub, message):
                json_message = (message.message)
                if 'data' in json_message:
                    self.excahgne_instance.get_price(self.currency, depthdata=json_message['data'],
                                                     amount_limit=self.excahgne_instance.AMOUNT_LIMITS[currency])

        for currency in currency_list:
            pubnub = PubNub(pnconfig)
            pubnub.add_listener(MySubscribeCallback(currency=currency, exchange_instance=self))
            pubnub.subscribe().channels(
                'depth_{}_{}'.format(currency.lower(), 'jpy' if currency is not "ETH" else "BTC")
            ).execute()

    def amount_can_buy(self, currency="BTC"):
        if currency == "BTC":
            return min(self.available["JPY"] * 0.8 / (self.last_ask + 1), self.BTC_AMOUNT_MAX)

    def amount_can_sell(self, currency="BTC"):
        if currency == "BTC":
            return min(self.available["BTC"], self.BTC_AMOUNT_MAX)

    def amount_can_market_buy(self, currency="BTC"):
        return self.amount_can_buy()

    def amount_can_market_sell(self, currency="BTC"):
        return self.amount_can_sell()


if __name__ == "__main__":
    bb = BitBank()
    print(bb.available)
    print(bb.last_bid, bb.last_ask)
    print(bb.take_order("BTC", 8000, 0.00014, side="buy"))
    bb.run_stream(['BTC'])
