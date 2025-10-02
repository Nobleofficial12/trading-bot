import requests

url = "http://localhost:5000/webhook"
data = {
    "signal_type": "longSignal",
    "price": 1900,
    "ema_trend": "up",
    "rsi": 65
}

response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response:", response.json())
