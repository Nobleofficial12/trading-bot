"""Bootstrap all TradingView CSV exports in a folder into the data cache.

Usage:
  python tools/bootstrap_all.py --dir "C:\path\to\exports"

This script will attempt to infer symbol and interval from filename using a simple pattern:
  SYMBOL__INTERVAL.csv  (e.g. XAU_USD__5min.csv) or you can pass --pattern to customize.
"""
import os
import argparse
from data_cache import bootstrap_from_csv


def infer_from_filename(name: str):
    base = os.path.splitext(os.path.basename(name))[0]
    if '__' in base:
        sym, interval = base.split('__', 1)
        sym = sym.replace('_', '/').upper()
        return sym, interval
    return None, None


def main(folder, dry_run=False):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.csv')]
    if not files:
        print('No CSV files found in', folder)
        return
    for path in files:
        sym, interval = infer_from_filename(path)
        if sym is None:
            print('Skipping (could not infer symbol/interval):', path)
            continue
        print(f'Bootstrapping {sym} {interval} from {path}...')
        if not dry_run:
            bootstrap_from_csv(sym, interval, path)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dir', required=True, help='Folder containing TradingView CSV exports')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    main(args.dir, dry_run=args.dry_run)
