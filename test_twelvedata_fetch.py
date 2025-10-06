"""Quick test: verify fetch_ohlc() can pull data from Twelve Data.

Usage:
  python3 test_twelvedata_fetch.py

The script will attempt to fetch 5min, 15min and 1h OHLC and print the last few rows.
Make sure your `TWELVE_DATA_API_KEY` is set in the environment or present in `myconfig.py`.
"""
import os
import sys
import traceback

try:
    # import the function from your signal engine
    from python_signal_engine import fetch_ohlc
except Exception:
    print("Failed to import fetch_ohlc from python_signal_engine.py")
    traceback.print_exc()
    sys.exit(1)


def mask_key(k):
    if not k:
        return '<missing>'
    return k[:4] + '...' + k[-4:]


def test_interval(interval, limit=10):
    print(f"\n--- Testing interval: {interval} (limit={limit}) ---")
    try:
        df = fetch_ohlc(interval=interval, limit=limit)
        if df is None:
            print("fetch_ohlc returned None")
            return
        print(f"Fetched {len(df)} rows")
        # show last rows
        with pd_print_options():
            print(df.tail(5).to_string())
    except Exception as e:
        print(f"Error fetching {interval}: {e}")
        traceback.print_exc()


from contextlib import contextmanager
import pandas as pd


@contextmanager
def pd_print_options():
    opts = pd.get_option('display.max_columns')
    pd.set_option('display.max_columns', 20)
    try:
        yield
    finally:
        pd.set_option('display.max_columns', opts)


def main():
    key_env = os.getenv('TWELVE_DATA_API_KEY')
    print('TWELVE_DATA_API_KEY (env):', mask_key(key_env))
    # Run tests for the three intervals
    for interval in ('5min', '15min', '1h'):
        test_interval(interval, limit=20)


if __name__ == '__main__':
    main()
