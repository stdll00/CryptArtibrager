from datetime import datetime
from email.utils import parsedate
import time
from collections import defaultdict
import datetime
import threading

class CryptPrice:
    ACTIVE_TIME_SECONDS = 0.3
    last_bid = 0.001
    last_ask = 10000000
    last_modified = 0  # UNIX TIME
    def __init__(self):
        pass

    def update(self, last_bid, last_ask, last_modified=None):
        self.last_bid = last_bid
        self.last_ask = last_ask
        if last_modified:
            self.last_modified = last_modified
        else:
            self.last_modified = time.time()

    def is_active(self):
        return (time.time() - self.last_modified) < self.ACTIVE_TIME_SECONDS

    def __repr__(self):
        return ",".join(map(str,(self.last_bid,self.last_ask,time.time()- self.last_modified)))


class CryptExchange():
    AMOUNT_LIMIT = 0

    NAME = "sample"
    PRIORITY = 0
    last_bid = 100
    last_ask = 10000000
    MIN_BTC_TRADE_AMOUNT = 0.001
    balance = defaultdict(float)
    available = defaultdict(float)
    position = defaultdict(float)

    last_price = defaultdict(CryptPrice)
    ASK_OFFSET = {"BTC": 0}
    BID_OFFSET = {"BTC": 1000}
    threads = []
    def __init__(self):
        self.balance = defaultdict(float)
        self.available = defaultdict(float)
        self.get_balance()

    def get_price(self):
        pass

    def take_order(self, currency, price, amount, side, *args, **kwargs):
        """
        指値で購入を試みる。
        購入に成功した場合は購入した数量(0< bought_amount <= amount) を返す。
        基本的には注文→数秒待つ→ キャンセル → 履歴を確認 の順に処理する

        :param currency: required - str
        :param price: required Number
        :param amount: required Number
        :param side: required - buy or sell
        :param args:
        :param kwargs:
        :return: 購入に成功した amount
        """
        amount = 0.0
        return amount

    def send_order(self, currency, price, amount, side, order_type):
        """
        発注する
        購入IDを返す。
        order_type == market (成行)
        の場合は全数量が約定する。

        :param currency:
        :param price:
        :param amount:
        :param side:
        :param order_type:
        :return:
        """
        """
        :param currency: required
        :param price:  required - numbers.number
        :param amount:  required - float
        :param side: required - buy or sell
        :param order_type: optional - limit (default) or market
        :return:
        """
        return

    def cancel_order(self, orderNo):
        """
        主にtake_order 利用時に使用
        注文をキャンセルする。

        :param orderNo:
        :return:
        """
        pass


    @staticmethod
    def _parse_http_datetime(s):
        return datetime(*parsedate(s)[:6])

    @staticmethod
    def get_time_diff(s):
        # unixtime = time.mktime(CryptExchange._parse_http_datetime(s).timetuple())
        timestamp = time.mktime(time.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")) - time.timezone
        return time.time() - timestamp
    @staticmethod
    def get_timestamp(s):
        # LastModifiled to unixtime
        return time.mktime(time.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")) - time.timezone
    def get_balance(self):
        pass

    def get_price(self, amount_limit=AMOUNT_LIMIT):
        """
        現在の価格情報を取得しキャッシュする。

        :param amount_limit:
        :return: bid,ask
        """
        return 0, 100000000

    def amount_can_buy(self):
        """
        BTCの購入可能高を取得する。

        :return: float
        """
        return 0

    def amount_can_sell(self):
        """
        BTCの売却可能高を取得する。
        :return: float
        """
        return 0

    def amount_can_market_buy(self):
        """
        BTCの成行注文での購入可能高を取得する。

        :return: float
        """
        return self.amount_can_buy()

    def amount_can_market_sell(self):
        """
        BTCの成行注文での購入可能高を取得する。

        :return: float
        """
        return self.amount_can_sell()

    def _stream(self,currency_list):
        return

    def run_stream(self,currency_list=[]):
        """
        stream APIがある場合にStreamに接続し、別スレッドで実行する

        :param currency_list:
        """
        t = threading.Thread(target=self._stream, args=(currency_list,), daemon=True)
        t.start()
        self.threads.append(t)



if __name__ == "__main__":
    print(CryptExchange.get_time_diff("Sun, 31 Dec 2017 07:18:41 GMT"))
