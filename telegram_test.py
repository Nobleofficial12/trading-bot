import requests
import config

TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = config.CHAT_ID
MESSAGE = "🚀 Test Alert: Your bot is working!"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE
}

print("📡 Sending request to Telegram...")
response = requests.post(url, data=payload)

print("✅ Status Code:", response.status_code)
print("📨 Response:", response.text)
