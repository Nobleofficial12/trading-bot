
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


from flask import Flask, request, jsonify, render_template_string
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from xauusd_bot import send_telegram_message

app = Flask(__name__)

# Simple status page for root URL
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>XAUUSD Trading Bot Status</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #000;
                color: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .navbar {
                background: #222831;
                padding: 1rem 2rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .navbar .bot-name {
                font-size: 1.5rem;
                font-weight: bold;
                color: #FFD700;
                letter-spacing: 2px;
            }
            .container {
                max-width: 600px;
                margin: 60px auto 0 auto;
                background: rgba(34, 40, 49, 0.95);
                border-radius: 16px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.2);
                padding: 2.5rem 2rem 2rem 2rem;
                text-align: center;
            }
            .turbine {
                margin: 2rem auto 1.5rem auto;
                width: 80px;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .fan {
                position: relative;
                width: 80px;
                height: 80px;
                margin: 0 auto;
                animation: spin 0.6s linear infinite;
            }
            .blade {
                position: absolute;
                width: 5px;
                height: 38px;
                background: linear-gradient(120deg, #bfc1c2 0%, #e0e0e0 60%, #888 100%);
                border-radius: 2.5px 2.5px 18px 18px;
                left: 37.5px;
                top: 2px;
                transform-origin: 50% 85%;
                opacity: 0.92;
                box-shadow: 0 0 6px #2228, 0 0 2px #fff8;
            }
            /* 12 blades for jet look */
            .fan .blade:nth-child(1)  { transform: rotate(0deg)   translateY(0); }
            .fan .blade:nth-child(2)  { transform: rotate(30deg)  translateY(0); }
            .fan .blade:nth-child(3)  { transform: rotate(60deg)  translateY(0); }
            .fan .blade:nth-child(4)  { transform: rotate(90deg)  translateY(0); }
            .fan .blade:nth-child(5)  { transform: rotate(120deg) translateY(0); }
            .fan .blade:nth-child(6)  { transform: rotate(150deg) translateY(0); }
            .fan .blade:nth-child(7)  { transform: rotate(180deg) translateY(0); }
            .fan .blade:nth-child(8)  { transform: rotate(210deg) translateY(0); }
            .fan .blade:nth-child(9)  { transform: rotate(240deg) translateY(0); }
            .fan .blade:nth-child(10) { transform: rotate(270deg) translateY(0); }
            .fan .blade:nth-child(11) { transform: rotate(300deg) translateY(0); }
            .fan .blade:nth-child(12) { transform: rotate(330deg) translateY(0); }
            .fan-hub {
                position: absolute;
                left: 32px;
                top: 32px;
                width: 16px;
                height: 16px;
                background: radial-gradient(circle at 60% 40%, #444 60%, #222 100%);
                border-radius: 50%;
                border: 2px solid #888;
                z-index: 2;
                box-shadow: 0 0 8px #222a;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            h1 {
                color: #FFD700;
                margin-bottom: 0.5rem;
            }
            .webhook {
                background: #393e46;
                color: #FFD700;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                font-family: monospace;
                margin: 1rem 0;
                display: inline-block;
            }
            .about {
                margin-top: 2.5rem;
                padding-top: 1.5rem;
                border-top: 1px solid #FFD70033;
                color: #bdbdbd;
                font-size: 1rem;
            }
            .about strong {
                color: #FFD700;
            }
        </style>
    </head>
    <body>
        <div class="navbar">
            <span class="bot-name">XAUUSD Trading Bot</span>
            <span class="creator" style="margin-left:auto; color:#FFD700; font-size:1.05rem; font-weight:500;">By O.A ISRAEL</span>
        </div>
        <div class="container">
            <div class="turbine">
                <div class="fan">
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="blade"></div>
                    <div class="fan-hub"></div>
                </div>
            </div>
            <h1>Trading Bot is Running</h1>
            <p>The webhook endpoint is ready to receive TradingView alerts.</p>
            <div class="webhook"><b>POST signals to:</b> <code>/webhook</code></div>
            <!-- About section removed, creator now in navbar -->
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

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
