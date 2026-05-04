import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "presidio_observer.db")

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                type TEXT,
                latency_ms REAL,
                language TEXT,
                entity_count INTEGER,
                has_pii INTEGER,
                entities TEXT,
                operators_used TEXT,
                items_anonymized INTEGER,
                flag TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                entity_type TEXT,
                score REAL,
                recognizer TEXT,
                created_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                entity_type TEXT,
                label TEXT,
                created_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
