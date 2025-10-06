import os
import pandas as pd
import requests
import time
import logging
import numpy as np
import hashlib
from datetime import datetime, timezone
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
import myconfig
from twelvedata import TDClient

# Configurable constants
SYMBOL = os.getenv('SYMBOL', getattr(myconfig, 'SYMBOL', 'XAU/USD'))
FETCH_LIMIT = int(os.getenv('FETCH_LIMIT', getattr(myconfig, 'FETCH_LIMIT', 20)))
TD_API_KEY = os.getenv('TWELVE_DATA_API_KEY', getattr(myconfig, 'TWELVE_DATA_API_KEY', None))
EMA_LENGTH = int(os.getenv('EMA_LENGTH', getattr(myconfig, 'EMA_LENGTH', 70)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def fetch_ohlc(symbol=SYMBOL, interval="5min", limit=FETCH_LIMIT):
    if not TD_API_KEY:
        logging.error("Twelve Data API key is missing. Set TWELVE_DATA_API_KEY in environment or myconfig.")
        return None
    # Use cache to assemble history; fetch only newest bars from API and append
    from data_cache import load_cache, append_to_cache
    td = TDClient(apikey=TD_API_KEY)

    # Load existing cache
    cached = load_cache(symbol, interval)
    # If cache exists and has enough rows, return last `limit` rows immediately
    if cached is not None and len(cached) >= limit:
        return cached.tail(limit).reset_index(drop=True)

    # Otherwise, fetch available bars from Twelve Data (smallest possible chunk) and append
    try:
        bars = td.time_series(symbol=symbol, interval=interval, outputsize=limit, order='ASC').as_pandas()
        bars = bars.reset_index()
        if 'datetime' not in bars.columns:
            bars = bars.rename(columns={bars.columns[0]: 'datetime'})
        bars['datetime'] = pd.to_datetime(bars['datetime'])
        bars[['open', 'high', 'low', 'close']] = bars[['open', 'high', 'low', 'close']].astype(float)
        bars['volume'] = 1
        bars = bars.tail(limit).reset_index(drop=True)
    except Exception as e:
        logging.warning(f"Failed to fetch from Twelve Data: {e}")
        # Fall back to cache if available
        if cached is not None:
            return cached.tail(limit).reset_index(drop=True)
        return None

    # If cache exists, append and return combined tail
    if cached is not None:
        combined = append_to_cache(symbol, interval, bars)
        return combined.tail(limit).reset_index(drop=True)

    # No cache existed: save the bars as cache and return
    append_to_cache(symbol, interval, bars)
    return bars

def detect_signals(df, ema_length=70, rsi_length=14, band_mult=1.2):
    # Minimum bars required: ATR rolling(window=ema_length*3) needs ema_length*3 bars
    min_bars = int(ema_length * 3)
    if df is None or len(df) < min_bars:
        logging.warning(
            "Insufficient bars for detect_signals: need at least %d bars (ema_length*3=%d), got %d. "
            "Return safe empty/NaN series. Consider increasing FETCH_LIMIT or decreasing ema_length.",
            min_bars, min_bars, 0 if df is None else len(df),
        )
        # Build safe return values matching expected shapes/indexes
        idx = df.index if (df is not None and hasattr(df, 'index')) else pd.Index([])
        long_entry = pd.Series(False, index=idx, dtype=bool)
        short_entry = pd.Series(False, index=idx, dtype=bool)
        zlema = pd.Series(np.nan, index=idx, dtype=float)
        trend = pd.Series(0, index=idx, dtype=int)
        rsi = pd.Series(np.nan, index=idx, dtype=float)
        return long_entry, short_entry, zlema, trend, rsi

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
    # Additional metadata may be added via kwargs (keeps compatibility)
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


# Simple in-memory dedupe store to avoid sending duplicate signals repeatedly.
# Keys are signal_id -> timestamp (UTC seconds)
_sent_signals = {}
_DEDUP_TTL = 120  # seconds

def _make_signal_id(symbol, timeframe, signal_type, bar_time):
    # bar_time is expected to be a pandas.Timestamp or datetime or ISO string
    if bar_time is None:
        bt = ''
    else:
        if hasattr(bar_time, 'isoformat'):
            bt = bar_time.isoformat()
        else:
            bt = str(bar_time)
    key = f"{symbol}|{timeframe}|{signal_type}|{bt}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def send_signal_to_webhook_with_metadata(signal_type, price, ema_trend, rsi, webhook_url, *, symbol=None, timeframe=None, bar_time=None, dry_run=False):
    """Send a webhook with extra metadata and idempotency.

    - Avoids sending the same (symbol,timeframe,signal,bar_time) more than once within TTL.
    - Adds an Idempotency-Key header and expanded JSON payload.
    - dry_run=True will only log the payload without POSTing.
    """
    signal_id = _make_signal_id(symbol or SYMBOL, timeframe or '', signal_type, bar_time)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    # cleanup old entries
    for k, t in list(_sent_signals.items()):
        if now_ts - t > _DEDUP_TTL:
            _sent_signals.pop(k, None)
    if signal_id in _sent_signals:
        logging.info(f"Skipping duplicate signal (recently sent): {signal_type} {symbol} {timeframe} {bar_time}")
        return False

    payload = {
        "signal_type": signal_type,
        "price": price,
        "ema_trend": ema_trend,
        "rsi": rsi,
        "symbol": symbol or SYMBOL,
        "timeframe": timeframe,
        "bar_time": bar_time.isoformat() if hasattr(bar_time, 'isoformat') else str(bar_time),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "signal_id": signal_id,
    }

    logging.info(f"Prepared signal payload: {payload}")
    if dry_run:
        logging.info("Dry-run enabled: not POSTing to webhook")
        _sent_signals[signal_id] = now_ts
        return True

    headers = {"Idempotency-Key": signal_id}
    max_attempts = 3
    backoff = 2
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            logging.info(f"Attempt {attempt}: POST {webhook_url} -> {resp.status_code}")
            if resp.status_code in (200, 201, 202):
                _sent_signals[signal_id] = now_ts
                return True
            else:
                logging.warning(f"Webhook returned {resp.status_code}: {resp.text}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} failed: {e}")
        time.sleep(backoff ** attempt)
    logging.error("All attempts to send webhook failed")
    return False

def main():
    webhook_url = os.getenv('WEBHOOK_URL', getattr(myconfig, 'WEBHOOK_URL', 'http://localhost:5000/webhook'))
    fail_count = 0
    while True:
        try:
            # Ensure we fetch enough bars for indicators (ATR rolling uses ema_length*3)
            required = int(EMA_LENGTH * 3)
            effective_limit = max(FETCH_LIMIT, required)
            logging.info(f"Using fetch limit={effective_limit} (configured {FETCH_LIMIT}, required {required})")
            # Fetch LTF (5min), MTF (15min), and HTF (1h) data
            df = fetch_ohlc(interval="5min", limit=effective_limit)
            df_mtf = fetch_ohlc(interval="15min", limit=effective_limit)
            df_htf = fetch_ohlc(interval="1h", limit=effective_limit)
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
