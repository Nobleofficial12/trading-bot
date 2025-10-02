import requests
import time
import itertools

# ------------------ CONFIG ------------------ #

# GoldAPI key (get a free one at https://www.goldapi.io/)
GOLDAPI_KEY = "goldapi-1cbghsmg8r9nks-io"

TELEGRAM_BOT_TOKEN = "8354165594:AAEqPeU7hhB6wilHdyJWEO6gCdqJPy8F_XE"
CHAT_ID = "7085719123"  # Your personal chat ID
FETCH_INTERVAL = 60  # seconds between price checks
# -------------------------------------------- #



def get_xauusd_price():
    """Fetch XAU/USD spot price from GoldAPI."""
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {
        "x-access-token": GOLDAPI_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if response.status_code == 200 and "price" in data:
            return float(data["price"])
        else:
            print(f"GoldAPI error: {data.get('error', 'No data returned.')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"GoldAPI request error: {e}")
        return None

def send_telegram_message(message):
    """Send a message to Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print(f"Telegram alert sent: {message}")
        else:
            print(f"Telegram error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")

if __name__ == "__main__":
    print("[WARNING] Do not run this script directly. Only tradingview_webhook.py should be running to receive and process alerts.")
    import sys
    sys.exit(1)
