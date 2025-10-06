import os

# Deprecated: prefer using myconfig.py which reads from environment variables.
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')
CHAT_ID = os.getenv('CHAT_ID')