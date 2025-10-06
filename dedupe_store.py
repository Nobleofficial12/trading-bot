import os
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = os.getenv('DEDUPE_DB_PATH', os.path.join(os.path.dirname(__file__), 'dedupe.db'))
_lock = threading.Lock()


def _ensure_db():
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sent_signals (
                    signal_id TEXT PRIMARY KEY,
                    ts INTEGER
                )
            ''')
            conn.commit()
        finally:
            conn.close()


def get(signal_id):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute('SELECT ts FROM sent_signals WHERE signal_id = ?', (signal_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set(signal_id, ts):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('INSERT OR REPLACE INTO sent_signals(signal_id, ts) VALUES (?, ?)', (signal_id, int(ts)))
        conn.commit()
    finally:
        conn.close()


def cleanup(older_than_ts):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('DELETE FROM sent_signals WHERE ts < ?', (int(older_than_ts),))
        conn.commit()
    finally:
        conn.close()
