import pandas as pd
import requests
import time
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

from twelvedata import TDClient
TD_API_KEY = "8905999fd8484f62af0d1eb49cbe7d77"  # Replace with your Twelve Data API key
def fetch_ohlc(symbol="XAU/USD", interval="5min", limit=100):
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
    response = requests.post(webhook_url, json=data)
    print(f"Sent {signal_type} signal: {response.status_code} {response.text}")

def main():
    webhook_url = "http://localhost:5000/webhook"  # Update if needed
    while True:
        try:
            # Fetch LTF (5min) and HTF (4h) data
            df = fetch_ohlc(interval="5min", limit=100)
            df_htf = fetch_ohlc(interval="4h", limit=100)
            long_entry, short_entry, zlema, trend, rsi = detect_signals(df)
            htf_trend = get_trend(df_htf)
            htf_trend_latest = htf_trend.iloc[-1]
            # Confirmed entries: LTF entry + HTF trend agreement
            if long_entry.iloc[-1] and htf_trend_latest == 1:
                send_signal_to_webhook("longSignal", df['close'].iloc[-1], trend.iloc[-1], rsi.iloc[-1], webhook_url)
            elif short_entry.iloc[-1] and htf_trend_latest == -1:
                send_signal_to_webhook("shortSignal", df['close'].iloc[-1], trend.iloc[-1], rsi.iloc[-1], webhook_url)
        except NotImplementedError:
            print("fetch_ohlc is not implemented. Please connect to your data source.")
            break
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
