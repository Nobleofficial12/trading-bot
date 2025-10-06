import os
import pandas as pd
import requests
import time
import logging
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
import myconfig
from twelvedata import TDClient

# Configurable constants
SYMBOL = os.getenv('SYMBOL', getattr(myconfig, 'SYMBOL', 'XAU/USD'))
FETCH_LIMIT = int(os.getenv('FETCH_LIMIT', getattr(myconfig, 'FETCH_LIMIT', 20)))
TD_API_KEY = os.getenv('TWELVE_DATA_API_KEY', getattr(myconfig, 'TWELVE_DATA_API_KEY', None))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def fetch_ohlc(symbol=SYMBOL, interval="5min", limit=FETCH_LIMIT):
    if not TD_API_KEY:
        logging.error("Twelve Data API key is missing. Set TWELVE_DATA_API_KEY in environment or myconfig.")
        return None
    td = TDClient(apikey=TD_API_KEY)
    bars = td.time_series(symbol=symbol, interval=interval, outputsize=limit, order='ASC').as_pandas()
    bars = bars[['open', 'high', 'low', 'close']].astype(float)
    bars['volume'] = 1
    bars = bars.tail(limit).reset_index(drop=True)
    return bars

def detect_signals(df, ema_length=70, rsi_length=14, band_mult=1.2):
    lag = int((ema_length - 1) / 2)
    src = df['close']
    zlema = EMAIndicator(src + (src - src.shift(lag)), window=ema_length).ema_indicator()
    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=ema_length).average_true_range()
    volatility = atr.rolling(window=ema_length*3).max() * band_mult

    # Compute crossover / crossunder against the deviation bands (stateful like Pine Script)
    upper_band = zlema + volatility
    lower_band = zlema - volatility

    # Boolean crossovers (requires previous bar comparison)
    cross_up = (df['close'] > upper_band) & (df['close'].shift(1) <= upper_band.shift(1))
    cross_down = (df['close'] < lower_band) & (df['close'].shift(1) >= lower_band.shift(1))

    # Initialize trend series and fill it iteratively so trend persists until a flip occurs
    trend = pd.Series(0, index=df.index, dtype=int)
    prev = 0
    for i in range(len(df)):
        if i == 0:
            # first bar: set based on crossover if present, otherwise 0
            if cross_up.iloc[i] and zlema.notna().iloc[i]:
                prev = 1
            elif cross_down.iloc[i] and zlema.notna().iloc[i]:
                prev = -1
            else:
                prev = 0
            trend.iloc[i] = prev
            continue
        if zlema.notna().iloc[i]:
            if cross_up.iloc[i]:
                prev = 1
            elif cross_down.iloc[i]:
                prev = -1
            # else keep previous prev
        # if zlema is nan keep prev as-is (can't determine yet)
        trend.iloc[i] = prev

    rsi = RSIIndicator(df['close'], window=rsi_length).rsi()

    # Entry signals: require crossover of price and ZLEMA, and require trend==1 (and was 1 previous)
    zlema_cross_up = (df['close'] > zlema) & (df['close'].shift(1) <= zlema.shift(1))
    zlema_cross_down = (df['close'] < zlema) & (df['close'].shift(1) >= zlema.shift(1))

    long_entry = zlema_cross_up & (trend == 1) & (trend.shift(1) == 1)
    short_entry = zlema_cross_down & (trend == -1) & (trend.shift(1) == -1)

    return long_entry, short_entry, zlema, trend, rsi

def send_signal_to_webhook(signal_type, price, ema_trend, rsi, webhook_url):
    data = {
        "signal_type": signal_type,
        "price": price,
        "ema_trend": ema_trend,
        "rsi": rsi
    }
    max_attempts = 3
    backoff = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            logging.info(f"Attempt {attempt}: Sent {signal_type} signal -> {response.status_code}")
            if response.status_code in (200, 201, 202):
                return True
            else:
                logging.warning(f"Webhook responded with status {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} failed to send webhook: {e}")
        time.sleep(backoff ** attempt)
    logging.error(f"Failed to send {signal_type} after {max_attempts} attempts.")
    return False

def main():
    webhook_url = os.getenv('WEBHOOK_URL', getattr(myconfig, 'WEBHOOK_URL', 'http://localhost:5000/webhook'))
    fail_count = 0
    while True:
        try:
            # Fetch LTF (5min), MTF (15min), and HTF (1h) data
            df = fetch_ohlc(interval="5min", limit=FETCH_LIMIT)
            df_mtf = fetch_ohlc(interval="15min", limit=FETCH_LIMIT)
            df_htf = fetch_ohlc(interval="1h", limit=FETCH_LIMIT)
            if any(x is None or len(x) < 5 for x in [df, df_mtf, df_htf]):
                logging.warning("Insufficient data fetched for one or more timeframes. Skipping this cycle.")
                fail_count += 1
                if fail_count >= 5:
                    logging.error("Too many consecutive data fetch failures. Exiting.")
                    break
                time.sleep(60)
                continue
            fail_count = 0
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

            logging.info(f"Last 3 bars - Long: 5m={long_5m.any()}, 15m={long_15m.any()}, 1h={long_1h.any()} | Agree={long_agree}")
            logging.info(f"Last 3 bars - Short: 5m={short_5m.any()}, 15m={short_15m.any()}, 1h={short_1h.any()} | Agree={short_agree}")

            # Send signal if any two timeframes agree
            if long_agree >= 2:
                logging.info("At least two timeframes agree on LONG. Sending signal...")
                send_signal_to_webhook("longSignal", df['close'].iloc[-1], trend_5m.iloc[-1], rsi_5m.iloc[-1], webhook_url)
            elif short_agree >= 2:
                logging.info("At least two timeframes agree on SHORT. Sending signal...")
                send_signal_to_webhook("shortSignal", df['close'].iloc[-1], trend_5m.iloc[-1], rsi_5m.iloc[-1], webhook_url)
        except NotImplementedError:
            logging.error("fetch_ohlc is not implemented. Please connect to your data source.")
            break
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
            fail_count += 1
            if fail_count >= 5:
                logging.error("Too many consecutive errors. Exiting.")
                break
        time.sleep(60)

if __name__ == "__main__":
    main()
