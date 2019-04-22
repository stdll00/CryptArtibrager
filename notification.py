
import requests

"""
LINEに通知を送る
"""
LINE_TOKEN = {}
LINE_TOKEN["main"]= ""
LINE_TOKEN["log"] = ""

def notify(message,room="main"):
    url = "https://notify-api.line.me/api/notify"
    token =LINE_TOKEN[room]
    headers = {"Authorization" : "Bearer "+ token}
    payload = {"message" : "\n"+message}
    r = requests.post(url ,headers = headers ,params=payload)

if __name__ == "__main__":
    notify("this is test message",room="log")