
import requests
import myconfig

data = {
    "signal_type": "longSignal",
    "price": 1900.0,
    "ema_trend": 1,
    "rsi": 65
}

webhook_url = getattr(myconfig, 'WEBHOOK_URL', 'https://willacademy.pythonanywhere.com/webhook')
print("Posting to:", webhook_url)
response = requests.post(webhook_url, json=data)
print("Status Code:", response.status_code)
print("Response:", response.text)
