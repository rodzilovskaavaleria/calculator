import sqlite3
from datetime import datetime

DB_NAME = "rates.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY,
            currency TEXT NOT NULL,
            rate REAL NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_rate(id, target_currency, rate):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    date_str = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO rates (id, currency, rate, fetched_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
        rate = excluded.rate,
        fetched_at = excluded.fetched_at
    """,
        (id, target_currency, rate, date_str),
    )
    conn.commit()
    conn.close()


def get_saved_rate(target_currency):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT rate FROM rates WHERE currency = ?", (target_currency,))
    result = cur.fetchone()
    conn.close()
    if result:
        return result[0]
    return None
