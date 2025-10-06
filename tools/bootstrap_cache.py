"""Bootstrap cache from a TradingView CSV export or generic OHLC CSV.

Usage:
  python tools/bootstrap_cache.py --symbol "XAU/USD" --interval 5min --file path/to/export.csv

The CSV should contain a `datetime` column (ISO format) and `open,high,low,close,volume` columns.
"""
import argparse
import sys
import os
from data_cache import bootstrap_from_csv


def main():
    parser = argparse.ArgumentParser(description='Bootstrap data cache from CSV')
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--interval', required=True)
    parser.add_argument('--file', required=True)
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        sys.exit(1)

    df = bootstrap_from_csv(args.symbol, args.interval, args.file)
    print(f"Bootstrapped cache for {args.symbol} {args.interval}, rows={len(df)}")

if __name__ == '__main__':
    main()
