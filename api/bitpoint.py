import os.path
import json
import requests, requests.exceptions
import time
import socket
import sys

try:
    from .model import CryptExchange
    from .model import CryptPrice
except SystemError:
    print("Import Error Using name api")
    from api.model import CryptExchange
    from api.model import CryptPrice

import threading

# 4桁
tradingPassword = "1234"

requests.packages.urllib3.disable_warnings()
BASE_PATH = "https://public.bitpoint.co.jp/bpj-api/"
HOST = "http://127.0.0.1"


class Bitpoint(CryptExchange):
    AMOUNT_LIMIT = 0
    BTC_AMOUNT_MAX = 1.1
    NAME = "BitPoint"
    PRIORITY=-1
    ASK_OFFSET = {"BTC":0}
    BID_OFFSET = {"BTC": 000}

    def __init__(self, forever=True):
        self.account_auth_info = json.load(
            open(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    ".auth.json")
            )
        )["bitpoint"]
        self.forever = forever

        while True:
            try:
                self.set_token()
                break
            except requests.exceptions.ConnectionError:
                print("server is down... retry")
                time.sleep(10)
        self.get_balance()
        self.last_bid, self.last_ask = self.get_price()

    def set_token(self, _debug=False):

        self.session = requests.session()
        res = self.session.get(BASE_PATH + "login", params=self.account_auth_info, verify=False)
        if (res.status_code) == 200:
            if "access_token" in json.loads(res.text):
                self.token = json.loads(res.text)
            else:
                print("token does not exits")
            if _debug:
                print("Token", self.token)
        else:
            raise ConnectionError
        if self.forever:
            t = threading.Timer(300, self.set_token)
            t.setDaemon(True)
            t.start()


    def get_balance(self, *args, **kwargs):
        for i in range(8):
            try:
                return self._get_balance(*args, **kwargs)
            except KeyError:
                time.sleep(5)
                print("bitpoint api is broken....", file=sys.stderr)

    def _get_balance(self, dump=False):
        """
        JPY , BTC , ETH
        :return:
        """
        result = {}
        available = {}
        data = json.dumps({
            "currencyCdList": [
                "JPY"
            ]
        })
        res = self.session.post(BASE_PATH + "/rc_balance_list", params=self.token, data=data,
                                headers={'content-type': 'application/json'}, verify=False)
        if dump:
            print(res.text)
        result["JPY"] = float(json.loads(res.text)["rcBalanceList"][0]["cashBalance"])
        available["JPY"] = float(json.loads(res.text)["rcBalanceList"][0]["availableCash"])

        # /vc_balance_list

        data = json.dumps({
            "calcCurrencyCd": "JPY",
            "currencyCdList": [
                "BTC",
            ]
        })

        res = self.session.post(BASE_PATH + "/vc_balance_list", params=self.token, data=data,
                                headers={'content-type': 'application/json'}, verify=False)
        if dump:
            print(res.text)
        for item in json.loads(res.text)["vcBalanceList"]:
            result[item["currencyCd1"]] = float(item["nominal"])
            available[item["currencyCd1"]] = float(item["nominal"])
        self.available = available
        self.balance = result
        return result

    @staticmethod
    def _get_price(currency="BTC", amount_limit=0):
        assert currency in ["BTC", "BCC", "ETH"]
        if amount_limit > 0:
            return 0, 100000000,0
        res = requests.get("{}/bitpoint/{}.json".format(HOST, currency))
        last_modified = CryptExchange.get_timestamp(res.headers['Last-Modified'])
        if CryptExchange.get_time_diff(res.headers['Last-Modified']) > 10:
            return 0, 10000000,last_modified
        try:
            json.loads(res.text)
        except json.decoder.JSONDecodeError as e:
            return 0, 10000000,last_modified

        for item in json.loads(res.text):
            if item["currencyCd1"] == currency:
                if item["buySellCls"] == "1":
                    sell = item["price"]
                elif item["buySellCls"] == "3":
                    buy = item["price"]
        return float(sell), float(buy),last_modified

    def get_price(self,currency="BTC",amount_limit=AMOUNT_LIMIT):
        sell, buy ,last_modified= self._get_price(currency=currency)
        if  currency=="BTC":
            self.last_bid, self.last_ask = sell, buy
        self.last_price[currency].update(sell,buy,last_modified)

        return sell, buy

    def send_order(self, currency, price, amount, side,order_type="limit"):
        assert side == 'buy' or side == 'sell'
        data = json.dumps({
            "tradingPassword": tradingPassword,
            "buySellCls": "3" if side == 'buy' else "1",
            "orderNominal": str(amount),
            "currencyCd1": currency,
            "currencyCd2": "JPY",
            "conditionCls": "1",
            "orderPriceIn": str(price),
            "durationCls": "1"
        })
        res = self.session.post(BASE_PATH + "spot_order?access_token=" + self.token["access_token"], data=data,
                                headers={'content-type': 'application/json'}, verify=False)
        print(res.text)
        res_json = json.loads(res.text)
        if res_json["resultCode"] == "0":
            print("Order Submitted")
            return res_json["orderNo"]
        else:
            print("Cannnot order")
            return None

    def cancel_order(self, orderNo):
        data = json.dumps({
            "tradingPassword": tradingPassword,
            "orderNo": str(orderNo)
        })
        res = self.session.post(BASE_PATH + "spot_order_cancel?access_token=" + self.token["access_token"],
                                data=data, headers={'content-type': 'application/json'}, verify=False)
        # print(orderNo,res.text)
        result = json.loads(res.text)
        return int(result["resultCode"])

    def take_order(self, currency, price, amount, side, _debug=True):
        """
        この取引所ではキャンセルに失敗することがあるので執拗にキャンセルリクエストを送る必要がある


        :param currency:  ex. "BTC"
        :param price:  ex. 300000
        :param amount: ex. 0.3
        :param side: 'buy'
        :param _debug:
        :return:
        """
        price = float(price)
        amount = float(amount)
        def update_available(execNominal):
            try:
                if side=='buy':
                    self.available["JPY"] -= execNominal*price
                elif side=='sell':
                    self.available[currency]-=execNominal
                    self.balance[currency]-=execNominal
                print('update balance')
                return execNominal
            except:
                import traceback
                traceback.print_exc()
                return execNominal

        orderNo = self.send_order(currency, price, amount, side)
        if orderNo is None:
            return 0
        for _ in range(20):
            tmp_amount = float(self.get_order(orderNo, currency=currency)["execNominal"])
            if tmp_amount == amount:
                print(_)
                return update_available(amount)
            elif tmp_amount>0:
                break
            time.sleep(0.4)

        flag_error = self.cancel_order(orderNo)
        if flag_error:
            print(orderNo, "Cancel Error!")
            time.sleep(3)
            tmp_amount = float(self.get_order(orderNo, currency)["execNominal"])
            threading.Timer(5, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(10, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(20, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(40, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(80, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(160, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(240, self.cancel_order, args=(orderNo,)).start()
            threading.Timer(320, self.cancel_order, args=(orderNo,)).start()
            if tmp_amount > 0:
                return update_available(tmp_amount)
            time.sleep(10)
            tmp_amount = float(self.get_order(orderNo, currency)["execNominal"])
            return update_available(tmp_amount)
        threading.Timer(3, self.cancel_order, args=(orderNo,)).start()
        threading.Timer(20, self.cancel_order, args=(orderNo,)).start()
        threading.Timer(80, self.cancel_order, args=(orderNo,)).start()
        threading.Timer(320, self.cancel_order, args=(orderNo,)).start()
        time.sleep(3)
        return update_available(float(self.get_order(orderNo, currency)["execNominal"]))

    def get_all_order(self, currency="BTC", period="5"):
        self.get_order(orderNo=None, currency=currency, period=period)

    def get_order(self, orderNo, currency="BTC", _debug=False, period="2"):
        """
        period 期間(0：当日、1：前日、2：1か月、3：3か月、4：6か月、5：1年)
        """
        data = json.dumps({
            "currencyCd1": currency,
            "currencyCd2": "JPY",
            "buySellClsSearch": "0",
            "orderStatus": "0",
            "period": period,
            "refTradeTypeCls": "3"
        })
        res = self.session.post(BASE_PATH + "vc_order_refer_list?access_token=" + self.token["access_token"], data=data,
                                headers={'content-type': 'application/json'}, verify=False)

        # print(res.text)
        if orderNo:
            for order in json.loads(res.text)["vcOrderList"]:
                if order["orderNo"] == orderNo:
                    return order
        else:
            total_buy_and_sell_jpy = 0
            total_jpy = 0
            for order in json.loads(res.text)["vcOrderList"]:
                print(json.dumps(order))
                if order["execNominal"] is None or order["orderPrice"] is None:
                    continue
                total_buy_and_sell_jpy += float(order["execNominal"]) * float(order["orderPrice"])
                total_jpy += float(order["execNominal"]) * float(order["orderPrice"]) * (
                1 if order["buySellCls"] == "1" else -1)
                if _debug:
                    print(order["orderNo"], order["orderNominal"], order["execNominal"])
            print(total_buy_and_sell_jpy, total_jpy)
            if _debug:
                print(json.loads(res.text)["vcOrderList"][0])

    def amount_can_buy(self):
        return min(self.available["JPY"] / (self.last_ask + 1), self.BTC_AMOUNT_MAX)

    def amount_can_sell(self):
        return min(self.available["BTC"], self.BTC_AMOUNT_MAX)

    def amount_can_market_buy(self):
        return 0

    def amount_can_market_sell(self):
        return 0

    def _stream(self,currency_list):
        print("Stream Start {}".format(self.NAME))
        while True:
            for currency in currency_list:
                self.get_price(currency)


    def simple_mm(self):
        position = -0.001
        while True:
            if self.last_ask - self.last_bid < 4000:
                time.sleep(1)
                continue
            if position < 0:
                tmp_position = bp.take_order(currency='BTC', amount=0.001, price=bp.last_bid + 0.01, side='buy')
            else:
                tmp_position = - bp.take_order(currency='BTC', amount=0.001, price=bp.last_ask -  0.01, side='sell')
            position += tmp_position
            print(position , tmp_position )
            time.sleep(0.1)

if __name__ == '__main__':
    import time

    bp = Bitpoint()
    bp.get_balance()
    print(bp.balance)
    print(bp.last_bid, bp.last_ask)
    print("can sell,buy : ", bp.amount_can_sell(), bp.amount_can_buy())
    print(bp.get_order(orderNo=None , currency="BTC" , period="5"))

    exit()
    bp.run_stream(['BTC',"ETH"])
    bp.simple_mm()
    while True:
        print(bp.last_price)
        time.sleep(1)
