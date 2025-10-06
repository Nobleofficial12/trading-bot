"""Demo script to exercise signal sending (dry-run) without calling external webhooks.

Run locally with your Python environment active:

powershell> python demo_send.py

This will build a sample payload and run the dedup logic with dry_run=True so nothing is posted.
"""
from datetime import datetime, timezone
from python_signal_engine import send_signal_to_webhook_with_metadata

if __name__ == '__main__':
    symbol = 'XAU/USD'
    timeframe = '5min'
    signal_type = 'longSignal'
    price = 1925.5
    ema_trend = 1
    rsi = 64.2
    bar_time = datetime.now(timezone.utc)

    ok = send_signal_to_webhook_with_metadata(signal_type, price, ema_trend, rsi, 'http://localhost:5000/webhook', symbol=symbol, timeframe=timeframe, bar_time=bar_time, dry_run=True)
    print('Dry-run send ok:', ok)
