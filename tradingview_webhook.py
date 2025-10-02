
# =====================
# TradingView Alert Template (set this as your alert message in TradingView):
# {
#   "signal_type": "{{strategy.order.action}}",   // e.g., "buy" or "sell"
#   "price": "{{close}}",
#   "ema_trend": "{{plot_0}}",                  // e.g., "up" or "down" or numeric
#   "rsi": "{{rsi}}",
#   "price_near_ema": "{{price_near_ema}}",      // true/false, set in Pine Script
#   "macd_signal": "{{macd_signal}}",            // optional, e.g., "bullish"/"bearish"
#   "volume_confirmed": "{{volume_confirmed}}"    // optional, true/false
# }
# =====================


from flask import Flask, request, jsonify
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from xauusd_bot import send_telegram_message

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON received'}), 400


    # Parse fields from TradingView alert JSON
    signal_type = data.get('signal_type')  # e.g., "buy", "sell", "longSignal", "shortSignal"
    price = float(data.get('price', 0))
    ema_trend = str(data.get('ema_trend', '')).lower()  # e.g., "up", "down", or numeric
    rsi = float(data.get('rsi', 0))
    price_near_ema = str(data.get('price_near_ema', 'true')).lower() == 'true'  # default True
    macd_signal = str(data.get('macd_signal', '')).lower()  # optional
    volume_confirmed = str(data.get('volume_confirmed', 'true')).lower() == 'true'  # default True

    # === Relay any valid TradingView alert directly to Telegram ===
    # Format the message using all received fields
    msg = (
        f"TradingView Signal\n"
        f"Signal Type: {signal_type}\n"
        f"Price: {price}\n"
        f"EMA Trend: {ema_trend}\n"
        f"RSI: {rsi}\n"
        f"Price Near EMA: {price_near_ema}\n"
        f"MACD: {macd_signal if macd_signal else 'N/A'}\n"
        f"Volume Confirmed: {volume_confirmed}"
    )
    print(f"Relaying TradingView alert to Telegram: {msg}")
    send_telegram_message(msg)

    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(port=5000)
