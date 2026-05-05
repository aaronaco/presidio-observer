from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any
import json

from database import init_db, get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Presidio Observer", lifespan=lifespan)

class ConfidenceFlag(str, Enum):
    confident = "confident"
    uncertain = "uncertain"
    anomaly = "anomaly"

class EntityPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    score: Optional[float] = None
    start: Optional[int] = None
    end: Optional[int] = None
    span_length: Optional[int] = None
    recognizer: Optional[str] = None
    pattern_name: Optional[str] = None
    original_score: Optional[float] = None
    score_context_improvement: Optional[float] = None
    validation_result: Optional[Any] = None

class ObserverEventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    correlation_id: Optional[str] = None
    type: str
    latency_ms: Optional[float] = None
    language: Optional[str] = None
    requested_entities: List[str] = Field(default_factory=list)
    score_threshold: Optional[float] = None
    allow_list_count: Optional[int] = None
    entity_count: Optional[int] = None
    has_pii: bool = False
    entities: List[EntityPayload] = Field(default_factory=list)
    flag: Optional[str] = None
    nlp_engine: Optional[str] = None
    context_enhancer: Optional[str] = None
    created_at: Optional[str] = None

class EventPayload(BaseModel):
    events: List[ObserverEventPayload]

class LabelPayload(BaseModel):
    entity_type: str
    label: str
    count: Optional[int] = 1
    entity_start: Optional[int] = None
    entity_end: Optional[int] = None

SUPPORTED_LABELS = {"correct", "false_positive", "missed"}
SUPPORTED_FLAGS = {item.value for item in ConfidenceFlag}

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def datetime_to_iso(value: Optional[datetime]):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def sanitize_entity(entity: EntityPayload):
    return {
        "type": entity.type,
        "score": entity.score,
        "start": entity.start,
        "end": entity.end,
        "span_length": entity.span_length,
        "recognizer": entity.recognizer,
        "pattern_name": entity.pattern_name,
        "original_score": entity.original_score,
        "score_context_improvement": entity.score_context_improvement,
        "validation_result": (
            str(entity.validation_result)
            if entity.validation_result is not None
            else None
        ),
    }

def sanitize_flag(flag: Optional[str]):
    if flag in SUPPORTED_FLAGS:
        return flag
    return None

def build_event_filters(
    since: Optional[datetime] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    filters = ["events.type = 'analyze'"]
    params = []

    if since:
        filters.append("events.created_at >= ?")
        params.append(datetime_to_iso(since))
    if language:
        filters.append("events.language = ?")
        params.append(language)
    if flag:
        filters.append("events.flag = ?")
        params.append(flag)
    if entity_type:
        filters.append("""
            EXISTS (
                SELECT 1
                FROM event_entities
                WHERE event_entities.event_id = events.id
                    AND event_entities.entity_type = ?
            )
        """)
        params.append(entity_type)

    return " AND ".join(filters), params

@app.post("/ingest")
def ingest_events(payload: EventPayload):
    with get_db() as conn:
        cursor = conn.cursor()
        for event in payload.events:
            if event.type != "analyze":
                continue

            entities = [sanitize_entity(entity) for entity in event.entities]
            requested_entities = event.requested_entities
            created_at = event.created_at or utc_now_iso()
            flag = sanitize_flag(event.flag)
            
            cursor.execute("""
                INSERT OR IGNORE INTO events (
                    id, correlation_id, type, latency_ms, language, requested_entities,
                    score_threshold, allow_list_count, entity_count, has_pii, entities,
                    flag, nlp_engine, context_enhancer, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id,
                event.correlation_id,
                event.type,
                event.latency_ms,
                event.language,
                json.dumps(requested_entities) if requested_entities else None,
                event.score_threshold,
                event.allow_list_count,
                len(entities),
                bool(entities),
                json.dumps(entities) if entities else None,
                flag,
                event.nlp_engine,
                event.context_enhancer,
                created_at
            ))
            if cursor.rowcount == 0:
                continue
            
            for ent in entities:
                cursor.execute("""
                    INSERT INTO event_entities (
                        event_id, entity_type, score, start, end, span_length,
                        recognizer, pattern_name, original_score,
                        score_context_improvement, validation_result, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id,
                    ent.get("type"),
                    ent.get("score"),
                    ent.get("start"),
                    ent.get("end"),
                    ent.get("span_length"),
                    ent.get("recognizer"),
                    ent.get("pattern_name"),
                    ent.get("original_score"),
                    ent.get("score_context_improvement"),
                    ent.get("validation_result"),
                    created_at
                ))
        conn.commit()
    return {"status": "ok"}

@app.get("/stats")
def get_stats(
    since: Optional[datetime] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[ConfidenceFlag] = None,
):
    flag_value = flag.value if flag else None
    where_clause, params = build_event_filters(since, language, entity_type, flag_value)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as count FROM events WHERE {where_clause}", params)
        analyze_count = cursor.fetchone()["count"]
        
        cursor.execute(f"SELECT AVG(latency_ms) as avg_latency FROM events WHERE {where_clause}", params)
        avg_latency = cursor.fetchone()["avg_latency"]
        
        return {
            "total_analyzed": analyze_count,
            "avg_latency_ms": avg_latency or 0.0
        }

@app.get("/entities/breakdown")
def entities_breakdown(
    since: Optional[datetime] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[ConfidenceFlag] = None,
):
    flag_value = flag.value if flag else None
    where_clause, params = build_event_filters(since, language, entity_type, flag_value)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT event_entities.entity_type, COUNT(*) as count
            FROM event_entities
            JOIN events ON events.id = event_entities.event_id
            WHERE {where_clause}
            GROUP BY event_entities.entity_type
            ORDER BY count DESC
        """, params)
        return [dict(row) for row in cursor.fetchall()]

@app.get("/events/recent")
def recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    since: Optional[datetime] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[ConfidenceFlag] = None,
):
    flag_value = flag.value if flag else None
    where_clause, params = build_event_filters(since, language, entity_type, flag_value)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM events WHERE {where_clause} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        )
        events = []
        for row in cursor.fetchall():
            d = dict(row)
            d["has_pii"] = bool(d.get("has_pii"))
            if d.get("entities"):
                d["entities"] = json.loads(d["entities"])
            if d.get("requested_entities"):
                d["requested_entities"] = json.loads(d["requested_entities"])
            events.append(d)
        return events

@app.post("/events/{event_id}/label")
def label_event(event_id: str, payload: LabelPayload):
    if payload.label not in SUPPORTED_LABELS:
        raise HTTPException(status_code=400, detail="Unsupported label")

    label_count = payload.count if payload.count is not None else 1
    if label_count < 1:
        raise HTTPException(status_code=400, detail="Label count must be at least 1")

    if payload.label in {"correct", "false_positive"}:
        label_count = 1
    label_entity_start = None if payload.label == "missed" else payload.entity_start
    label_entity_end = None if payload.label == "missed" else payload.entity_end

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM events WHERE id = ?", (event_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Event not found")

        if payload.label == "missed":
            cursor.execute("""
                DELETE FROM labels
                WHERE event_id = ?
                    AND entity_type = ?
                    AND label = 'missed'
                    AND entity_start IS NULL
                    AND entity_end IS NULL
            """, (
                event_id,
                payload.entity_type,
            ))
        else:
            cursor.execute("""
                DELETE FROM labels
                WHERE event_id = ?
                    AND entity_type = ?
                    AND label IN ('correct', 'false_positive')
                    AND (
                        entity_start = ?
                        OR (entity_start IS NULL AND ? IS NULL)
                    )
                    AND (
                        entity_end = ?
                        OR (entity_end IS NULL AND ? IS NULL)
                    )
            """, (
                event_id,
                payload.entity_type,
                label_entity_start,
                label_entity_start,
                label_entity_end,
                label_entity_end,
            ))

        cursor.execute("""
            INSERT INTO labels (
                event_id, entity_type, entity_start, entity_end, label, count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            payload.entity_type,
            label_entity_start,
            label_entity_end,
            payload.label,
            label_count,
            utc_now_iso()
        ))
        conn.commit()
    return {"status": "ok"}

@app.get("/events/{event_id}/labels")
def event_labels(event_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, event_id, entity_type, entity_start, entity_end, label,
                COALESCE(count, 1) as count, created_at
            FROM labels
            WHERE event_id = ?
            ORDER BY created_at DESC, id DESC
        """, (event_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.delete("/events/{event_id}/labels/{label_id}")
def remove_event_label(event_id: str, label_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM labels WHERE id = ? AND event_id = ?",
            (label_id, event_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Label not found")

        cursor.execute(
            "DELETE FROM labels WHERE id = ? AND event_id = ?",
            (label_id, event_id),
        )
        conn.commit()

    return {"status": "ok"}

@app.get("/evaluation/summary")
def evaluation_summary(
    since: Optional[datetime] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[ConfidenceFlag] = None,
):
    flag_value = flag.value if flag else None
    where_clause, params = build_event_filters(since, language, None, flag_value)
    label_filters = [where_clause]
    label_params = [*params]

    if entity_type:
        label_filters.append("labels.entity_type = ?")
        label_params.append(entity_type)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT labels.label, SUM(COALESCE(labels.count, 1)) as count
            FROM labels
            JOIN events ON events.id = labels.event_id
            WHERE {" AND ".join(label_filters)}
            GROUP BY labels.label
        """, label_params)
        counts = {row["label"]: row["count"] for row in cursor.fetchall()}
        
        tp = counts.get("correct", 0)
        fp = counts.get("false_positive", 0)
        fn = counts.get("missed", 0)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f2 = (5 * precision * recall) / ((4 * precision) + recall) if (precision + recall) > 0 else 0
        
        return {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f2_score": round(f2, 4)
        }
