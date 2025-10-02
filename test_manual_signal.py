import requests

data = {
    "signal_type": "longSignal",
    "price": 1900.0,
    "ema_trend": 1,
    "rsi": 65
}

response = requests.post("http://localhost:5000/webhook", json=data)
print("Status Code:", response.status_code)
print("Response:", response.text)
