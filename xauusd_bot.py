import os
import requests
import time
import itertools
import myconfig

# ------------------ CONFIG ------------------ #
# Use environment variables first, then fall back to myconfig
GOLDAPI_KEY = os.getenv('GOLDAPI_KEY', getattr(myconfig, 'GOLDAPI_KEY', 'goldapi-1cbghsmg8r9nks-io'))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', getattr(myconfig, 'TELEGRAM_BOT_TOKEN', None))
CHAT_ID = os.getenv('CHAT_ID', getattr(myconfig, 'CHAT_ID', None))
FETCH_INTERVAL = int(os.getenv('FETCH_INTERVAL', getattr(myconfig, 'FETCH_INTERVAL', 60)))
# -------------------------------------------- #



def get_xauusd_price():
    """Fetch XAU/USD spot price from GoldAPI."""
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {
        "x-access-token": GOLDAPI_KEY,
        "Content-Type": "application/json"
    }
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            if response.status_code == 200 and "price" in data:
                return float(data["price"])
            else:
                print(f"GoldAPI error (attempt {attempt}): {data.get('error', 'No data returned.')}")
        except requests.exceptions.RequestException as e:
            print(f"GoldAPI request error (attempt {attempt}): {e}")
        time.sleep(1 * attempt)
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

def check_and_alert_price_change():
    """Check for big price changes and send Telegram alert if ±1% change detected."""
    import os
    last_price_file = "last_xauusd_price.txt"
    current_price = get_xauusd_price()
    if current_price is None:
        return

    # Load last price from file
    if os.path.exists(last_price_file):
        with open(last_price_file, "r") as f:
            try:
                last_price = float(f.read().strip())
            except Exception:
                last_price = current_price
    else:
        last_price = current_price

    # Calculate percent change
    if last_price > 0:
        percent_change = ((current_price - last_price) / last_price) * 100
        if abs(percent_change) >= 1:
            direction = "up" if percent_change > 0 else "down"
            msg = f"⚡️ Gold price moved {direction} {percent_change:.2f}%!\nPrev: {last_price:.2f}\nNow: {current_price:.2f}"
            send_telegram_message(msg)

    # Save current price for next check
    with open(last_price_file, "w") as f:
        f.write(str(current_price))


def send_market_status_message(status):
    """Send a Telegram message on market open/close."""
    msg = f"🔔 Gold market {status}!"
    send_telegram_message(msg)

def is_market_open():
    """Return True if market is open (Monday-Friday, 24h UTC)."""
    import datetime
    now = datetime.datetime.utcnow()
    # Gold market typically closed from Friday 22:00 UTC to Sunday 22:00 UTC
    weekday = now.weekday()  # Monday=0, Sunday=6
    hour = now.hour
    minute = now.minute
    # Market closes Friday 22:00 UTC, opens Sunday 22:00 UTC
    if (weekday == 4 and hour >= 22) or (weekday == 5) or (weekday == 6 and hour < 22):
        return False
    return True


def send_daily_summary():
    """Send a daily summary message at a set UTC time (e.g., 23:59 UTC)."""
    import datetime
    now = datetime.datetime.utcnow()
    msg = f"📊 Daily summary for {now.strftime('%Y-%m-%d')}: Gold market monitored."
    send_telegram_message(msg)

def main_signal_engine():
    """Automated loop for price change, market status, and daily summary alerts."""
    import time
    import datetime
    last_market_status = None
    last_summary_date = None
    while True:
        market_open = is_market_open()
        now = datetime.datetime.utcnow()
        # Market open/close alerts
        if market_open and last_market_status != "open":
            send_market_status_message("open")
            last_market_status = "open"
        elif not market_open and last_market_status != "closed":
            send_market_status_message("closed")
            last_market_status = "closed"
        # Price change alerts
        if market_open:
            check_and_alert_price_change()
        # Daily summary alert at 23:59 UTC
        if now.hour == 23 and now.minute == 59:
            if last_summary_date != now.date():
                send_daily_summary()
                last_summary_date = now.date()
        time.sleep(FETCH_INTERVAL)

# To run 24/7 on PythonAnywhere, set main_signal_engine() as your always-on task or run it in your main app.
