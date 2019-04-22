from unittest import TestCase
import unittest
from api.bitbank import BitBank
from time import sleep

class TestBitBank(TestCase):
    def setUp(self):
        self.bitbank = BitBank(True)

    def test_get_price(self):
        bid, ask = self.bitbank.get_price()
        self.assertGreater(ask,bid)

        bid, ask = self.bitbank.get_price(currency='MONA')
        self.assertGreater(ask,bid)

    def test_stream(self):
        tmp = []
        bitbank = BitBank(True)
        bitbank.get_price = lambda *args,**kwargs:tmp.append([args,kwargs])
        bitbank.run_stream(["BTC"])
        self.assertTrue(bool(bitbank.threads))
        sleep(2)
        self.assertTrue(tmp[0][1]['depthdata'])

if __name__ == '__main__':
    unittest.main()

