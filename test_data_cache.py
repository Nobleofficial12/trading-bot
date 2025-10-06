import os
import tempfile
import pandas as pd
import shutil

from data_cache import _cache_path, save_cache, load_cache, append_to_cache, bootstrap_from_csv


def make_sample_df(start_ts=0, n=5, freq='5T'):
    idx = pd.date_range('2020-01-01', periods=n, freq=freq)
    df = pd.DataFrame({
        'datetime': idx,
        'open': range(n),
        'high': range(1, n+1),
        'low': range(n),
        'close': [x + 0.5 for x in range(n)],
        'volume': [1]*n
    })
    return df


def test_append_and_dedupe(tmp_path, monkeypatch):
    # Prepare temp cache dir
    tmp_cache = tmp_path / 'cache'
    monkeypatch.setenv('DATA_CACHE_DIR', str(tmp_cache))
    tmp_cache.mkdir()

    symbol = 'TEST/FOO'
    interval = '5min'
    df1 = make_sample_df(n=5)
    # Save initial
    save_cache(symbol, interval, df1)
    loaded = load_cache(symbol, interval)
    assert len(loaded) == 5

    # Append overlapping rows (last two same, plus two new)
    df2 = make_sample_df(n=4)
    df2['datetime'] = df2['datetime'] + pd.Timedelta(minutes=10)
    appended = append_to_cache(symbol, interval, df2)
    # No duplicate datetimes
    assert appended['datetime'].is_unique
    assert appended.index.is_monotonic_increasing


def test_bootstrap_from_csv(tmp_path, monkeypatch):
    tmp_cache = tmp_path / 'cache'
    monkeypatch.setenv('DATA_CACHE_DIR', str(tmp_cache))
    tmp_cache.mkdir()
    symbol = 'BOOT/ME'
    interval = '15min'
    df = make_sample_df(n=6)
    csv_path = tmp_path / 'boot.csv'
    df.to_csv(csv_path, index=False)

    # Bootstrap
    booted = bootstrap_from_csv(symbol, interval, str(csv_path))
    assert len(booted) == 6
    loaded = load_cache(symbol, interval)
    assert len(loaded) == 6
