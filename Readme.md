# BitCoin自動取引Bot
実際に1年超運用し、累計4億円程度の取引実績があるBotプログラムです。  
1取引の利益は薄いが暴騰時や乱高下時には一晩で数万円の利益が出ることもあります。


## 概要
bitbank.cc quoinex bitpointの3取引所間でアービトラージを狙う。  
ポジションを持っているとポジション料を取られるので適宜自分で送金を行うなどしてポジションをなくすことで損失を防ぐことも重要。


## 設計
### 設計思想
低リスクにビットコイン取引を行う。  
取引にかかる数十秒間の価格変動リスク以外を負わないようにしたい。

取引所間に価格差があるときに安い方で購入 ー> 高い方で売却 を行うことで利益を目指す。
売却するにはビットコインを所持している必要があるように思えるが実際には空売りを使い、ビットコイン保有リスクを負うことを避ける。
これによりポジション料で損するリスクを負うが、ポジション料よりも儲かるときにのみ取引を行うことで解決する。

流動性の高い取引所でのみ成行決済を行う。


### 使い方
設定ファイル(api/.auth.json)及び bitpoint.jsのusename,パスワードハッシュを埋める
bitpoint.pyの取引番号も埋める必要がある。


- 仮想マシンを用意しnodejs,npm,python3,python3-pipをインストール 
- `getdata`をnpm start実行し、websocketでbitpointのデータを書き込む
- nginx等で前行のデータをホスト
- arbitrage.pyを実行


pm2等を使うと永続化、プロセス監視が行いやすいです。



## Sample 
売取引所 買取引所 取引を実行する価格差(1BTCあたり)のしきい値 期間内の価格差の最大値 取引可能高 現在の価格差
の順で3個の取引なので6通りが表示されています。
このサンプルでは入金されていないので売買できませんが実際にはしきい値を超えたときに売買が行われます。

```
sell:BitPoint  buy:Quoinex    2200  1011   0.0   112
sell:BitBank   buy:Quoinex    3000  2365   0.0   331
sell:Quoinex   buy:BitPoint   1600  -229   0.0  -848
sell:BitBank   buy:BitPoint   2000  1421   0.0  -428
sell:Quoinex   buy:BitBank    2400  -505   0.0  -775
sell:BitPoint  buy:BitBank    2000  -415   0.0  -574
2019-04-23 22:20:22	0.77	0.0		0.4718	4.597e-05		0.18578	3e-08
JPY: 1
BTC :4.6e-05


sell:BitPoint  buy:Quoinex    2200  1068   0.0   499
sell:BitBank   buy:Quoinex    3000  3074   0.0  2064
sell:Quoinex   buy:BitPoint   1600   277   0.0 -1410
sell:BitBank   buy:BitPoint   2000  1942   0.0   756
sell:Quoinex   buy:BitBank    2400    45   0.0 -2702
sell:BitPoint  buy:BitBank    2000  -574   0.0 -2099
2019-04-23 22:37:44	0.77	0.0		0.4718	4.597e-05		0.18578	3e-08
JPY: 1
BTC :4.6e-05


sell:BitPoint  buy:Quoinex    2200   872   0.0   329
sell:BitBank   buy:Quoinex    3000  2872   0.0  1769
sell:Quoinex   buy:BitPoint   1600  -358   0.0 -1257
sell:BitBank   buy:BitPoint   2000  2010   0.0   639
sell:Quoinex   buy:BitBank    2400 -1924   0.0 -2354
sell:BitPoint  buy:BitBank    2000 -1633   0.0 -1896
2019-04-23 22:52:33	0.77	0.0		0.4718	4.597e-05		0.18578	3e-08
JPY: 1
BTC :4.6e-05


```
