import json
import time
import os.path
from collections import defaultdict
from quoine.client import Quoinex as Quoinex_api
from api.model import CryptExchange
import datetime
from datetime import timedelta
from quoine.exceptions import QuoineAPIException

"""
戦略

購入:
    信用売りがあったら信用売をネットアウト
    現物購入

売却:
    信用買いがあったらネットアウト
    現物があったら現物を売る
    信用売り
"""


def to_defaultdict_float(_dict):
    dd = defaultdict(float)
    dd.update(_dict)
    return dd


class Quoinex(CryptExchange):
    BTC_AMOUNT_MAX_SELL = 0.9
    BTC_AMOUNT_MAX_BUY = 0.5
    BTC_AMOUNT_MAX = min(BTC_AMOUNT_MAX_BUY, BTC_AMOUNT_MAX_SELL)
    balance = defaultdict(float)
    available = defaultdict(float)

    currency_to_id = {
        "BTC": 5,
        "ETH": 29
    }
    NAME = "Quoinex"
    PRIORITY = 1.5
    MIN_ORDER_SIZE = to_defaultdict_float({'BTC': 0.001})
    BID_OFFSET_DEFAULT = to_defaultdict_float({'BTC': 400})
    ASK_OFFSET_DEFAULT = to_defaultdict_float({'BTC': 1000})
    ASK_OFFSET_DIFF_POSITION = to_defaultdict_float({'BTC': 400})  # IF POSITION is minus
    BID_OFFSET_DIFF_POSITION = to_defaultdict_float({'BTC': 400})  # IF POSITION is plus

    BID_OFFSET = to_defaultdict_float({'BTC': 0})  # init
    ASK_OFFSET = to_defaultdict_float({'BTC': 0})  # init

    last_checked = datetime.datetime.today() - timedelta(seconds=1000)

    def __init__(self):
        account = json.load(
            open(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    ".auth.json")
            )
        )["quoine"]
        self.client = Quoinex_api(account["id"], account["key"])
        self.client.API_URL = 'https://api.liquid.com'
        self.balance = self.get_balance()
        self.last_bid, self.last_ask = self.get_price()

    def get_balance(self):
        """
        supports
        ETHBTC
        QASHETH
        UBTCQASH
        BTCJPY
        BTCUSD
        BTCSGD

        """

        self.balance = defaultdict(float)
        self.available = defaultdict(float)
        self.balance_for_logging = {}
        for currency_and_balance in self.client.get_account_balances():
            if not float(currency_and_balance["balance"]) == 0:
                self.balance[currency_and_balance["currency"]] = float(currency_and_balance["balance"])
                self.available[currency_and_balance["currency"]] = float(currency_and_balance["balance"])

        positions = self.client.get_trading_accounts()
        for position_data in positions:
            if position_data["currency_pair_code"] == "BTCJPY":
                self.position["BTC"] = float(position_data["position"])
                self.balance["BTC"] += float(position_data["position"])
                self.available["JPY"] = float(position_data["free_margin"])
                self.balance["JPY"] += float(position_data["margin"]) * float(position_data["max_leverage_level"]) * (
                    1 if float(position_data["position"]) < 0 else -1)

        for currency in self.balance:
            if currency == "JPY":
                continue
            if self.position[currency] <= -0.01:
                self.ASK_OFFSET[currency] = \
                    self.ASK_OFFSET_DEFAULT[currency] - self.ASK_OFFSET_DIFF_POSITION[currency]
            else:
                self.ASK_OFFSET[currency] = self.ASK_OFFSET_DEFAULT[currency]

            if self.balance[currency] >= 0.01:
                self.BID_OFFSET[currency] = \
                    self.BID_OFFSET_DEFAULT[currency] - self.BID_OFFSET_DIFF_POSITION[currency]
            else:
                self.BID_OFFSET[currency] = self.BID_OFFSET_DEFAULT[currency]

        return self.balance

    def get_price(self, currency="BTC", amount_limit=0, ticker_data=None, depth_data=None):
        product_id = self.currency_to_id[currency]

        # for rate limit
        if datetime.datetime.today() - self.last_checked < timedelta(seconds=1.1):
            return self.last_bid, self.last_ask
        try:
            result = self.client.get_product(product_id)
        except QuoineAPIException:
            return 1, 10000000
        self.last_checked = datetime.datetime.today()
        bid, ask = map(float, (result["market_bid"], result["market_ask"]))
        if currency == "BTC":
            self.last_bid, self.last_ask = bid, ask
        return bid, ask

    def send_order(self, currency, price, amount, side, force_margin=False, order_type='limit',
                   auto_split=False):

        if amount < self.MIN_ORDER_SIZE[currency]:
            return
        product_id = self.currency_to_id[currency]

        def custom_margin_order(order_type, product_id, side, quantity, price, leverage_level=2, price_range=None,
                                funding_currency=None, order_direction='netout'):
            data = {
                'order': {
                    'order_type': order_type,
                    'product_id': product_id,
                    'side': side,
                    'quantity': quantity,
                    'leverage_level': leverage_level,
                    'order_direction': order_direction
                }
            }
            if price and order_type == Quoinex_api.ORDER_TYPE_LIMIT:
                data['order']['price'] = price
            if price_range and order_type == Quoinex_api.ORDER_TYPE_MARKET_RANGE:
                data['order']['price_range'] = price_range
            if funding_currency:
                data['order']['funding_currency'] = funding_currency

            return self.client._post('orders', True, json=data)

        def margin_order(price_this_order, amount_this_order, side_this_order):
            order = custom_margin_order(order_type=order_type, product_id=product_id, price=price_this_order,
                                        side=side_this_order, quantity=amount_this_order, order_direction="netout")
            print(order)
            return order["id"]

        if side == "sell" and self.available[currency] >= amount and not force_margin:
            self.balance[currency] -= amount
            if order_type == 'limit':
                return self.client.create_limit_sell(product_id, str(amount), str(price))['id']
            elif order_type == 'market':
                return self.client.create_market_sell(product_id=product_id, quantity=str(amount))['id']
        elif side == 'buy' and self.balance[currency] >= -self.MIN_ORDER_SIZE[currency] and not force_margin:
            self.available['JPY'] -= amount * price
            if order_type == 'limit':
                return self.client.create_limit_buy(product_id, str(amount), str(price))['id']
            elif auto_split and self.position[currency] < -0.001 and (-self.position[currency]) < amount:
                """
                レバレッジ買いでポジションを消す+現物買い
                """
                print("auto split")
                amount_remains = amount - (-self.position[currency])
                tmp = self.client.create_market_buy(product_id=product_id, quantity=str(-self.position[currency]))['id']
                return self.client.create_market_buy(product_id=product_id, quantity=str(amount_remains))['id']
            elif order_type == 'market':
                return self.client.create_market_buy(product_id=product_id, quantity=str(amount))['id']

        if order_type == 'market':
            self.available[currency] += amount * (1 if side == 'buy' else -1)
            self.balance[currency] += amount * (1 if side == 'buy' else -1)
            self.available['JPY'] -= amount * price * 1.1
        return margin_order(price, amount_this_order=amount, side_this_order=side)

    def take_order(self, currency, price, amount, side, force_margin=False, *args, **kwargs):
        if amount < self.MIN_ORDER_SIZE[currency]:
            return 0

        order_id = self.send_order(currency=currency, price=price, amount=amount, side=side, force_margin=force_margin,
                                   order_type="limit")
        if not order_id:
            print("order not submitted")
            return 0
        for i in range(5):
            time.sleep(0.7)
            order_result = self.client.get_order(order_id)
            if order_result['status'] == 'filled':
                return float(order_result['filled_quantity'])
            assert order_result['status'] == 'live'
        print("cancel order")
        self.cancel_order(order_id)
        order_result = self.client.get_order(order_id)
        print(order_result)
        return float(order_result['filled_quantity'])

    def cancel_order(self, orderNo):
        self.client.cancel_order(orderNo)

    def amount_can_sell(self):
        if self.available['BTC'] > 0.01:
            return self.available['BTC'] + self.position['BTC'] * (self.position['BTC'] > 0)

        return max(0,
                   min((self.available["JPY"] - 230000) / self.last_bid, self.BTC_AMOUNT_MAX_SELL),
                   min(self.balance['BTC'], self.BTC_AMOUNT_MAX_SELL)
                   )

    def amount_can_buy(self):
        if self.position["BTC"] < -0.01:
            return min(-self.position["BTC"], self.BTC_AMOUNT_MAX_BUY)
        return max(0,
                   min(-self.balance["BTC"], self.BTC_AMOUNT_MAX_BUY),
                   min((self.available["JPY"] - 80000) / self.last_ask, self.BTC_AMOUNT_MAX_BUY)
                   )

    def amount_can_market_buy(self):
        return self.amount_can_buy()

    def amount_can_market_sell(self):
        return self.amount_can_sell()


if __name__ == '__main__':
    qx = Quoinex()
    print(qx.balance)

    def genbutsu_to_margin(amount):
        price = (qx.last_ask + qx.last_bid) / 2
        qx.client.create_limit_sell(5, str(amount), str(price))
        print(qx.take_order("BTC", price, amount, side="buy", force_margin=True))

    # マイナスポジションと現物をぶつけて消す
    def margin_to_genbutsu(amount):
        price = (qx.last_ask + qx.last_bid) / 2
        qx.client.create_limit_buy(5, str(amount), str(price))
        print(qx.take_order("BTC", price, amount, side="sell", force_margin=True))

