"""
Debug runner: fetches data, runs detect_signals on 5m/1h, prints status, optionally sends webhook.

Usage:
  python debug_signal_run.py        # prints diagnostics
  python debug_signal_run.py --send # also POSTs to webhook if HTF-confirmed entry

- Prints detailed debug output for 5m and 1h timeframes (last up to 5 bars)
- Only sends webhook if --send is passed and HTF confirmation is present
- Robust to missing/short data and fetch failures
"""
import os
import sys
import argparse
import traceback
import logging
from python_signal_engine import fetch_ohlc, detect_signals, send_signal_to_webhook
import myconfig

# Configurable constants
SYMBOL = os.getenv('SYMBOL', getattr(myconfig, 'SYMBOL', 'XAU/USD'))
FETCH_LIMIT = int(os.getenv('FETCH_LIMIT', getattr(myconfig, 'FETCH_LIMIT', 20)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def mask(v):
    if not v:
        return '<missing>'
    return v[:4] + '...' + v[-4:]


def print_debug(df, z, t, label, n):
    logging.info(f"--- {label} Debug (last up to {n} bars) ---")
    logging.info("idx | close     | zlema     | trend")
    for i in range(-n, 0):
        idx = df.index[i]
        logging.info(f"{idx:3} | {df['close'].iloc[i]:9.2f} | {z.iloc[i]:9.2f} | {t.iloc[i]:5}")


def main(send=False):
    webhook_url = os.getenv('WEBHOOK_URL', getattr(myconfig, 'WEBHOOK_URL', None))
    logging.info(f'Using webhook_url: {webhook_url}')
    df5 = None
    df1h = None
    le5 = se5 = z5 = t5 = r5 = None
    le1h = se1h = z1h = t1h = r1h = None
    confirmed_long_5m = confirmed_short_5m = None
    n5 = n1h = 0
    try:
        df5 = fetch_ohlc(symbol=SYMBOL, interval='5min', limit=FETCH_LIMIT)
        df1h = fetch_ohlc(symbol=SYMBOL, interval='1h', limit=FETCH_LIMIT)
        if df5 is None or df1h is None or len(df5) < 5 or len(df1h) < 5:
            logging.warning(f'Insufficient data fetched for debug output. Got {len(df5) if df5 is not None else 0} rows for 5m, {len(df1h) if df1h is not None else 0} rows for 1h. Check your data source and API key.')
            return
        le5, se5, z5, t5, r5 = detect_signals(df5)
        le1h, se1h, z1h, t1h, r1h = detect_signals(df1h)
        confirmed_long_5m = le5 & (t1h == 1)
        confirmed_short_5m = se5 & (t1h == -1)
        n5 = min(5, len(df5))
        n1h = min(5, len(df1h))
    except Exception as e:
        logging.error('Failed to fetch OHLC or compute signals:', exc_info=True)
        logging.error('Check your Twelve Data API key and network connection.')
        return
    # Print debug info
    print_debug(df5, z5, t5, '5m', n5)
    print_debug(df1h, z1h, t1h, '1h', n1h)
    # Only look at last 3 bars for confirmed entries
    long_5m = confirmed_long_5m.iloc[-3:]
    short_5m = confirmed_short_5m.iloc[-3:]
    long_agree = long_5m.any()
    short_agree = short_5m.any()
    logging.info('=== HTF Confirmation Summary ===')
    logging.info(f'Long signal (5m entry & 1h trend==1): {long_agree}')
    logging.info(f'Short signal (5m entry & 1h trend==-1): {short_agree}')
    logging.info('Last few rows (5m):\n' + df5.tail(3).to_string())
    logging.info('ZLEMA last value (5m): %s', z5.iloc[-1])
    logging.info('Trend last (5m): %s', t5.iloc[-1])
    logging.info('RSI last (5m): %s', r5.iloc[-1])
    if send:
        if long_agree:
            logging.info('Sending LONG signal to webhook (HTF confirmed)...')
            ok = send_signal_to_webhook('longSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            logging.info('Webhook send ok: %s', ok)
        elif short_agree:
            logging.info('Sending SHORT signal to webhook (HTF confirmed)...')
            ok = send_signal_to_webhook('shortSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            logging.info('Webhook send ok: %s', ok)
        else:
            logging.info('Not sending: no HTF-confirmed entry')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='POST to webhook if HTF-confirmed entry')
    args = parser.parse_args()
    main(send=args.send)
