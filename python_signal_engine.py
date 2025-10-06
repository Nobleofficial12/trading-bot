import os
import pandas as pd
import requests
import time
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
import myconfig

from twelvedata import TDClient
TD_API_KEY = os.getenv('TWELVE_DATA_API_KEY', getattr(myconfig, 'TWELVE_DATA_API_KEY', None))
def fetch_ohlc(symbol="XAU/USD", interval="5min", limit=200):
    td = TDClient(apikey=TD_API_KEY)
    bars = td.time_series(symbol=symbol, interval=interval, outputsize=limit, order='ASC').as_pandas()
    bars = bars[['open', 'high', 'low', 'close']].astype(float)
    bars['volume'] = 1
    bars = bars.tail(limit).reset_index(drop=True)
    return bars

def get_trend(df, ema_length=70, band_mult=1.2):
    lag = int((ema_length - 1) / 2)
    src = df['close']
    zlema = EMAIndicator(src + (src - src.shift(lag)), window=ema_length).ema_indicator()
    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=ema_length).average_true_range()
    volatility = atr.rolling(window=ema_length*3).max() * band_mult
    trend = pd.Series(0, index=df.index)
    trend[zlema.notna() & (df['close'] > (zlema + volatility))] = 1
    trend[zlema.notna() & (df['close'] < (zlema - volatility))] = -1
    return trend

def detect_signals(df, ema_length=70, rsi_length=14, band_mult=1.2):
    # Zero-lag EMA approximation
    lag = int((ema_length - 1) / 2)
    src = df['close']
    zlema = EMAIndicator(src + (src - src.shift(lag)), window=ema_length).ema_indicator()
    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=ema_length).average_true_range()
    volatility = atr.rolling(window=ema_length*3).max() * band_mult
    trend = pd.Series(0, index=df.index)
    trend[zlema.notna() & (df['close'] > (zlema + volatility))] = 1
    trend[zlema.notna() & (df['close'] < (zlema - volatility))] = -1
    rsi = RSIIndicator(df['close'], window=rsi_length).rsi()
    # Entry signals (exact crossover/crossunder logic)
    long_entry = (
        (df['close'] > zlema) & (df['close'].shift(1) <= zlema.shift(1))
        & (trend == 1) & (trend.shift(1) == 1)
    )
    short_entry = (
        (df['close'] < zlema) & (df['close'].shift(1) >= zlema.shift(1))
        & (trend == -1) & (trend.shift(1) == -1)
    )
    return long_entry, short_entry, zlema, trend, rsi

def send_signal_to_webhook(signal_type, price, ema_trend, rsi, webhook_url):
    data = {
        "signal_type": signal_type,
        "price": price,
        "ema_trend": ema_trend,
        "rsi": rsi
    }
    # Robust POST with retries
    max_attempts = 3
    backoff = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            print(f"Attempt {attempt}: Sent {signal_type} signal -> {response.status_code}")
            if response.status_code in (200, 201, 202):
                return True
            else:
                print(f"Webhook responded with status {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt} failed to send webhook: {e}")
        time.sleep(backoff ** attempt)
    print(f"Failed to send {signal_type} after {max_attempts} attempts.")
    return False

def main():
    # Webhook URL can be set via environment variable or in myconfig as WEBHOOK_URL
    webhook_url = os.getenv('WEBHOOK_URL', getattr(myconfig, 'WEBHOOK_URL', 'http://localhost:5000/webhook'))
    while True:
        try:
            # Fetch LTF (5min), MTF (15min), and HTF (1h) data
            df = fetch_ohlc(interval="5min", limit=100)
            df_mtf = fetch_ohlc(interval="15min", limit=100)
            df_htf = fetch_ohlc(interval="1h", limit=100)
            # Run full entry logic on all three timeframes
            long_entry_5m, short_entry_5m, zlema_5m, trend_5m, rsi_5m = detect_signals(df)
            long_entry_15m, short_entry_15m, zlema_15m, trend_15m, rsi_15m = detect_signals(df_mtf)
            long_entry_1h, short_entry_1h, zlema_1h, trend_1h, rsi_1h = detect_signals(df_htf)

            # Check last 3 bars for entry conditions
            long_5m = long_entry_5m.iloc[-3:]
            long_15m = long_entry_15m.iloc[-3:]
            long_1h = long_entry_1h.iloc[-3:]
            short_5m = short_entry_5m.iloc[-3:]
            short_15m = short_entry_15m.iloc[-3:]
            short_1h = short_entry_1h.iloc[-3:]

            # Count how many timeframes have a long/short entry in last 3 bars
            long_agree = sum([long_5m.any(), long_15m.any(), long_1h.any()])
            short_agree = sum([short_5m.any(), short_15m.any(), short_1h.any()])

            print(f"Last 3 bars - Long: 5m={long_5m.any()}, 15m={long_15m.any()}, 1h={long_1h.any()} | Agree={long_agree}")
            print(f"Last 3 bars - Short: 5m={short_5m.any()}, 15m={short_15m.any()}, 1h={short_1h.any()} | Agree={short_agree}")

            # Send signal if any two timeframes agree
            if long_agree >= 2:
                print("At least two timeframes agree on LONG. Sending signal...")
                send_signal_to_webhook("longSignal", df['close'].iloc[-1], trend_5m.iloc[-1], rsi_5m.iloc[-1], webhook_url)
            elif short_agree >= 2:
                print("At least two timeframes agree on SHORT. Sending signal...")
                send_signal_to_webhook("shortSignal", df['close'].iloc[-1], trend_5m.iloc[-1], rsi_5m.iloc[-1], webhook_url)
        except NotImplementedError:
            print("fetch_ohlc is not implemented. Please connect to your data source.")
            break
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
