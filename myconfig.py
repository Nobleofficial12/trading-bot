"""
Central configuration for the trading bot.

This file intentionally reads values from environment variables when possible.
Set the following environment variables in your deployment or in a local .env file:

- WEBHOOK_URL
- TELEGRAM_BOT_TOKEN
- TWELVE_DATA_API_KEY
- CHAT_ID
- SYMBOL (optional, default: XAU/USD)
- FETCH_LIMIT (optional, default: 20)

Do NOT commit secrets to source control. Use environment variables or a secrets manager.
"""
import os

WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://example.com/webhook')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')
CHAT_ID = os.getenv('CHAT_ID')

# Optional tuning
SYMBOL = os.getenv('SYMBOL', 'XAU/USD')
# Ensure FETCH_LIMIT is large enough for indicators (ema_length * 3). Default set to 210 for EMA_LENGTH=70.
FETCH_LIMIT = int(os.getenv('FETCH_LIMIT', '210'))
EMA_LENGTH = int(os.getenv('EMA_LENGTH', '70'))
