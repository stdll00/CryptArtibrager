import os, json
import python_bitbankcc


API_KEY = os.environ['BITBANK_API_KEY']
API_SECRET = os.environ['BITBANK_API_SECRET']

prv = python_bitbankcc.private(API_KEY, API_SECRET)

# PRIVATE TEST

value = prv.get_asset()
print(json.dumps(value))

value = prv.get_order(
    'btc_jpy', # ペア
    '71084903' # 注文ID
)
print(json.dumps(value))

value = prv.get_active_orders(
    'btc_jpy' # ペア
)
print(json.dumps(value))

value = prv.order(
    'btc_jpy', # ペア
    '131594', # 価格
    '0.0001', # 注文枚数
    'buy', # 注文サイド
    'market' # 注文タイプ
)
print(json.dumps(value))

value = prv.cancel_order(
    'btc_jpy', # ペア
    '133493980' # 注文ID
)
print(json.dumps(value))

value = prv.cancel_orders(
    'btc_jpy', # ペア
    ['133503762', '133503949'] # 注文IDのリスト
)
print(json.dumps(value))

value = prv.get_orders_info(
    'btc_jpy', # ペア
    ['133511828', '133511986'] # 注文IDのリスト
)
print(json.dumps(value))

value = prv.get_trade_history(
    'btc_jpy', # ペア
    '10' # 取得する約定数
)

value = prv.get_withdraw_account(
    'btc' # アセットタイプ
)
print(json.dumps(value))

value = prv.request_withdraw(
    'btc', # アセットタイプ
    'e9fb5d9f-0509-4cb5-8325-ec13ade4354c', # 引き出し先UUID
    '10.123', # 引き出し数
    { # 有効になっていた場合に必須
        'otp_token': '387427',
        'sms_token': '836827'
    }
)
print(json.dumps(value))