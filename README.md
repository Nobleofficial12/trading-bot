# Trading Bot

This repository contains scripts for monitoring XAU/USD, generating signals and relaying them to Telegram.

Key files
- `python_signal_engine.py` - Signal engine that fetches OHLC from Twelve Data and sends signals to a webhook.
- `tradingview_webhook.py` - Flask app that accepts TradingView/webhook signals and relays them to Telegram.
- `xauusd_bot.py` - Helper utilities for fetching XAU/USD price and sending Telegram messages.
- `myconfig.py` - Local config file (not committed if it contains secrets). Use environment variables in production.

Recommended environment variables (optional, fall back to `myconfig.py`):
- `TWELVE_DATA_API_KEY` - Twelve Data API key
- `WEBHOOK_URL` - URL for webhook relay
- `WEBHOOK_SECRET` - Optional secret header to protect the webhook
- `GOLDAPI_KEY` - GoldAPI key for price fetch
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `CHAT_ID` - Telegram chat id
- `FETCH_INTERVAL` - Price fetch interval in seconds

Improvements made
- Configs now read from environment variables with `myconfig.py` fallback.
- Added retries and backoff for external HTTP calls (Twelve Data, GoldAPI, webhook POSTs).
- Webhook now supports optional secret header validation.
- Improved logging for signal decisions to aid debugging.

How to run
1. Install requirements: `pip install -r requirements.txt`
2. Ensure `myconfig.py` exists with the required keys or export env vars.
3. Run the webhook: `python tradingview_webhook.py` (or deploy to PythonAnywhere/Heroku)
4. Run the signal engine: `python python_signal_engine.py`

Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# set env vars (example)
$env:TWELVE_DATA_API_KEY = 'your_key_here'
$env:TELEGRAM_BOT_TOKEN = 'your_telegram_token'
$env:CHAT_ID = 'your_chat_id'
python debug_signal_run.py
```

Run tests

```powershell
python -m pytest -q

Bootstrap cache from TradingView export

1. In TradingView, open the chart you use and the timeframe (e.g., 5m). Click the three-dots menu on the chart -> "Export" -> save the CSV.
2. Run the bootstrap tool to import the CSV into the local cache:

```powershell
python tools/bootstrap_cache.py --symbol "XAU/USD" --interval 5min --file path\to\tradingview_export_5m.csv
```

This will create a CSV in `data_cache/` that the engine will use to compute indicators immediately.
```

Security note
- Don't commit secrets to Git. Use `myconfig.py` locally and environment variables in production.

