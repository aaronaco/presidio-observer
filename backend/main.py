from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import json
import time

from database import init_db, get_db

app = FastAPI(title="Presidio Observer")

@app.on_event("startup")
def startup_event():
    init_db()

class EventPayload(BaseModel):
    events: List[Dict[str, Any]]

class LabelPayload(BaseModel):
    entity_type: str
    label: str
    count: Optional[int] = 1
    entity_start: Optional[int] = None
    entity_end: Optional[int] = None

SUPPORTED_LABELS = {"correct", "false_positive", "missed"}

def build_event_filters(
    since: Optional[str] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    filters = ["events.type = 'analyze'"]
    params = []

    if since:
        filters.append("events.created_at >= ?")
        params.append(since)
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
async def ingest_events(payload: EventPayload):
    with get_db() as conn:
        cursor = conn.cursor()
        for event in payload.events:
            if event.get("type") != "analyze":
                continue

            entities = event.get("entities", [])
            requested_entities = event.get("requested_entities", [])
            
            cursor.execute("""
                INSERT INTO events (
                    id, correlation_id, type, latency_ms, language, requested_entities,
                    score_threshold, allow_list_count, entity_count, has_pii, entities,
                    flag, nlp_engine, context_enhancer, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event["id"],
                event.get("correlation_id"),
                event["type"],
                event.get("latency_ms"),
                event.get("language"),
                json.dumps(requested_entities) if requested_entities else None,
                event.get("score_threshold"),
                event.get("allow_list_count"),
                event.get("entity_count"),
                event.get("has_pii", False),
                json.dumps(entities) if entities else None,
                event.get("flag"),
                event.get("nlp_engine"),
                event.get("context_enhancer"),
                event.get("created_at")
            ))
            
            for ent in entities:
                cursor.execute("""
                    INSERT INTO event_entities (
                        event_id, entity_type, score, start, end, span_length,
                        recognizer, pattern_name, original_score,
                        score_context_improvement, validation_result, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["id"],
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
                    event.get("created_at")
                ))
        conn.commit()
    return {"status": "ok"}

@app.get("/stats")
async def get_stats(
    since: Optional[str] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    where_clause, params = build_event_filters(since, language, entity_type, flag)

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
async def entities_breakdown(
    since: Optional[str] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    where_clause, params = build_event_filters(since, language, entity_type, flag)

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
async def recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    since: Optional[str] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    where_clause, params = build_event_filters(since, language, entity_type, flag)

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
async def label_event(event_id: str, payload: LabelPayload):
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
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ))
        conn.commit()
    return {"status": "ok"}

@app.get("/events/{event_id}/labels")
async def event_labels(event_id: str):
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
async def remove_event_label(event_id: str, label_id: int):
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
async def evaluation_summary(
    since: Optional[str] = None,
    language: Optional[str] = None,
    entity_type: Optional[str] = None,
    flag: Optional[str] = None,
):
    where_clause, params = build_event_filters(since, language, None, flag)
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
