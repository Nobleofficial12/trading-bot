"""Debug runner: fetch data, run detect_signals on 5m/15m/1h, print status, optionally send webhook.

Usage:
  python debug_signal_run.py        # prints diagnostics
  python debug_signal_run.py --send # also POSTs to webhook if agreement >=2
"""
import os
import sys
import argparse
import traceback

from python_signal_engine import fetch_ohlc, detect_signals, send_signal_to_webhook
import myconfig


def mask(v):
    if not v:
        return '<missing>'
    return v[:4] + '...' + v[-4:]


def main(send=False):
    webhook_url = os.getenv('WEBHOOK_URL', getattr(myconfig, 'WEBHOOK_URL', None))
    print('Using webhook_url:', webhook_url)
    try:
        df5 = fetch_ohlc(interval='5min', limit=100)
        df15 = fetch_ohlc(interval='15min', limit=100)
        df1h = fetch_ohlc(interval='1h', limit=100)
    except Exception as e:
        print('Failed to fetch OHLC:', e)
        traceback.print_exc()
        sys.exit(1)

    le5, se5, z5, t5, r5 = detect_signals(df5)
    le15, se15, z15, t15, r15 = detect_signals(df15)
    le1h, se1h, z1h, t1h, r1h = detect_signals(df1h)

    long_5m = le5.iloc[-3:]
    long_15m = le15.iloc[-3:]
    long_1h = le1h.iloc[-3:]
    short_5m = se5.iloc[-3:]
    short_15m = se15.iloc[-3:]
    short_1h = se1h.iloc[-3:]

    long_agree = sum([long_5m.any(), long_15m.any(), long_1h.any()])
    short_agree = sum([short_5m.any(), short_15m.any(), short_1h.any()])

    print('\n=== Agreement Summary ===')
    print(f'Long agree count: {long_agree} (5m={long_5m.any()},15m={long_15m.any()},1h={long_1h.any()})')
    print(f'Short agree count: {short_agree} (5m={short_5m.any()},15m={short_15m.any()},1h={short_1h.any()})')

    print('\nLast few rows (5m):')
    print(df5.tail(3).to_string())
    print('\nZLEMA last value (5m):', z5.iloc[-1])
    print('Trend last (5m):', t5.iloc[-1])
    print('RSI last (5m):', r5.iloc[-1])

    if send:
        if long_agree >= 2:
            print('\nSending LONG signal to webhook...')
            ok = send_signal_to_webhook('longSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            print('Webhook send ok:', ok)
        elif short_agree >= 2:
            print('\nSending SHORT signal to webhook...')
            ok = send_signal_to_webhook('shortSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            print('Webhook send ok:', ok)
        else:
            print('\nNot sending: less than 2 timeframes agree')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='POST to webhook if agreement >=2')
    args = parser.parse_args()
    main(send=args.send)
