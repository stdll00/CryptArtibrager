#!/usr/bin/env python3
import datetime
import api.bitbank
import api.bitpoint
import api.quoinex




def output(bitpoint,bitbank,quoinex=None):
    bb = bitbank.balance
    bp = bitpoint.balance
    s = "	"
    result_string = "".join(map(str,[datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),s,bp["JPY"],s , bp["BTC"],s,"",s ,bb["JPY"],s , bb["BTC"],s , ""]))
    if quoinex is not None:
        qx = quoinex.balance
        result_string+= "".join(map(str,[s,qx["JPY"],s , qx["BTC"],s,""]))
    else:
        from collections import defaultdict
        qx= defaultdict(float)
    print(result_string)

    total_JPY = bp["JPY"]+bb["JPY"]+qx["JPY"]
    total_BTC = bp["BTC"]+bb["BTC"]+qx["BTC"]
    total_string = "JPY: "+str(int(total_JPY))+"\n"+\
                    "BTC :"+str(total_BTC)+"\n"
    return result_string,total_string



def total(BTC=1500000,ETH=0):
    price = {}
    price["JPY"]=1
    price["BTC"]=BTC
    # price["ETH"]=ETH




if __name__=="__main__":
    import sys
    bitbank = api.bitbank.BitBank()
    bitpoint = api.bitpoint.Bitpoint(forever=False)
    quoinex =  api.quoinex.Quoinex()
    sys.stderr.write(output(bitpoint,bitbank,quoinex)[1])
    sys.stderr.write("\n")