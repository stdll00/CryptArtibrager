from notification import notify
from arbitrage import *


at = Arbitrager([quoinex, bitpoint])
quoinex.take_order('BTC', 1000, 0.001, side='buy')

start_balance = at.start_balance
if not (-0.25 < bitpoint.balance['BTC'] + bitbank.balance['BTC'] + quoinex.balance['BTC'] < 0.25):
    raise ValueError
at.update_price()

try:
    [print() for _ in range(len(at) * (len(at) - 1) + 1)]
    while True:
        for i in range(LOOP_COUNT):
            status_code, message = at.run()
            if i % 10 == 0:
                print("\033[A" * len(at) * (len(at) - 1), flush=True, end='')
                print(message, end='')
            time.sleep(0.1)
        at.update_balance()
        tsucho_message, tsucho_total = get_all_balance.output(bitpoint, bitbank, quoinex)
        balance_diff, balance_diff_in_string = at.balance_diff(start_balance)
        print(tsucho_total)
        [print() for _ in range(len(at) * (len(at) - 1) + 1)]
        notify(message + '\n' * 2 + tsucho_message + '\n' + tsucho_total + '\n' + balance_diff_in_string, room='log')

except:
    balance_diff, balance_diff_in_string = at.balance_diff(start_balance)
    import traceback, sys

    traceback.print_exc()
    ex, ms, tb = sys.exc_info()
    if ex is not KeyboardInterrupt:
        notify("Program Exit", room="main")
    notify("Program Exit: " + balance_diff_in_string, room='log')
    print(balance_diff_in_string)
finally:
    pass