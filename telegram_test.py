import requests

# Replace with your bot token
TOKEN = "8354165594:AAEqPeU7hhB6wilHdyJWEO6gCdqJPy8F_XE"
# Replace with your chat ID
CHAT_ID = "7085719123"
# Message to send
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
