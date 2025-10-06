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
        df5 = fetch_ohlc(interval='5min', limit=200)
        df15 = fetch_ohlc(interval='15min', limit=200)
        df1h = fetch_ohlc(interval='1h', limit=200)
    except Exception as e:
        print('Failed to fetch OHLC:', e)
        traceback.print_exc()
        sys.exit(1)

    le5, se5, z5, t5, r5 = detect_signals(df5)
    le1h, se1h, z1h, t1h, r1h = detect_signals(df1h)

    # HTF confirmation: only consider entries where 5m entry and 1h trend agree
    confirmed_long_5m = le5 & (t1h == 1)
    confirmed_short_5m = se5 & (t1h == -1)


    # Only look at last 3 bars for confirmed entries
    long_5m = confirmed_long_5m.iloc[-3:]
    short_5m = confirmed_short_5m.iloc[-3:]
    long_agree = long_5m.any()
    short_agree = short_5m.any()

    print('\n=== HTF Confirmation Summary ===')
    print(f'Long signal (5m entry & 1h trend==1): {long_agree}')
    print(f'Short signal (5m entry & 1h trend==-1): {short_agree}')

    print('\nLast few rows (5m):')
    print(df5.tail(3).to_string())
    print('\nZLEMA last value (5m):', z5.iloc[-1])
    print('Trend last (5m):', t5.iloc[-1])
    print('RSI last (5m):', r5.iloc[-1])

    if send:
        if long_agree:
            print('\nSending LONG signal to webhook (HTF confirmed)...')
            ok = send_signal_to_webhook('longSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            print('Webhook send ok:', ok)
        elif short_agree:
            print('\nSending SHORT signal to webhook (HTF confirmed)...')
            ok = send_signal_to_webhook('shortSignal', df5['close'].iloc[-1], t5.iloc[-1], r5.iloc[-1], webhook_url)
            print('Webhook send ok:', ok)
        else:
            print('\nNot sending: no HTF-confirmed entry')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='POST to webhook if agreement >=2')
    args = parser.parse_args()
    main(send=args.send)
