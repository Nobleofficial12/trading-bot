import os
import pandas as pd
from typing import Optional

CACHE_DIR = os.getenv('DATA_CACHE_DIR', os.path.join(os.path.dirname(__file__), 'data_cache'))
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(symbol: str, interval: str) -> str:
    safe_symbol = symbol.replace('/', '_').replace(':', '_')
    filename = f"{safe_symbol}__{interval}.csv"
    return os.path.join(CACHE_DIR, filename)


def load_cache(symbol: str, interval: str) -> Optional[pd.DataFrame]:
    path = _cache_path(symbol, interval)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=['datetime'])
    # Ensure types
    for c in ['open', 'high', 'low', 'close']:
        if c in df.columns:
            df[c] = df[c].astype(float)
    return df


def save_cache(symbol: str, interval: str, df: pd.DataFrame, max_rows: int = 2000):
    path = _cache_path(symbol, interval)
    # keep only last max_rows
    if len(df) > max_rows:
        df = df.tail(max_rows).reset_index(drop=True)
    df.to_csv(path, index=False)


def append_to_cache(symbol: str, interval: str, df_new: pd.DataFrame):
    """Append new rows to cache, dedupe by datetime, and save."""
    df_existing = load_cache(symbol, interval)
    if df_existing is None:
        save_cache(symbol, interval, df_new)
        return df_new
    # Concatenate and dedupe by datetime
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined = df_combined.drop_duplicates(subset=['datetime'], keep='last')
    df_combined = df_combined.sort_values('datetime').reset_index(drop=True)
    save_cache(symbol, interval, df_combined)
    return df_combined


def bootstrap_from_csv(symbol: str, interval: str, csv_path: str):
    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    save_cache(symbol, interval, df)
    return df
