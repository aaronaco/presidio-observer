import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "presidio_observer.db")

EVENT_COLUMNS = {
    "correlation_id": "TEXT",
    "requested_entities": "TEXT",
    "score_threshold": "REAL",
    "allow_list_count": "INTEGER",
    "nlp_engine": "TEXT",
    "context_enhancer": "TEXT",
}

EVENT_ENTITY_COLUMNS = {
    "start": "INTEGER",
    "end": "INTEGER",
    "span_length": "INTEGER",
    "pattern_name": "TEXT",
    "original_score": "REAL",
    "score_context_improvement": "REAL",
    "validation_result": "TEXT",
}

LABEL_COLUMNS = {
    "count": "INTEGER",
    "entity_start": "INTEGER",
    "entity_end": "INTEGER",
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_events_language ON events (language)",
    "CREATE INDEX IF NOT EXISTS idx_events_flag ON events (flag)",
    "CREATE INDEX IF NOT EXISTS idx_event_entities_event_id ON event_entities (event_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_entities_entity_type ON event_entities (entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_labels_event_id ON labels (event_id)",
]

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                correlation_id TEXT,
                type TEXT,
                latency_ms REAL,
                language TEXT,
                requested_entities TEXT,
                score_threshold REAL,
                allow_list_count INTEGER,
                entity_count INTEGER,
                has_pii INTEGER,
                entities TEXT,
                flag TEXT,
                nlp_engine TEXT,
                context_enhancer TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                entity_type TEXT,
                score REAL,
                start INTEGER,
                end INTEGER,
                span_length INTEGER,
                recognizer TEXT,
                pattern_name TEXT,
                original_score REAL,
                score_context_improvement REAL,
                validation_result TEXT,
                created_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                entity_type TEXT,
                entity_start INTEGER,
                entity_end INTEGER,
                label TEXT,
                count INTEGER,
                created_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        """)
        _ensure_columns(cursor, "events", EVENT_COLUMNS)
        _ensure_columns(cursor, "event_entities", EVENT_ENTITY_COLUMNS)
        _ensure_columns(cursor, "labels", LABEL_COLUMNS)
        _ensure_indexes(cursor)
        conn.commit()

def _ensure_columns(cursor, table_name, columns):
    existing_columns = {
        row["name"]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

def _ensure_indexes(cursor):
    for statement in INDEXES:
        cursor.execute(statement)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
