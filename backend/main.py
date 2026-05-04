from fastapi import FastAPI
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

SUPPORTED_LABELS = {"correct", "false_positive"}

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
async def get_stats(since: Optional[str] = None):
    # Basic implementation
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM events WHERE type='analyze'")
        analyze_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT AVG(latency_ms) as avg_latency FROM events WHERE type='analyze'")
        avg_latency = cursor.fetchone()["avg_latency"]
        
        return {
            "total_analyzed": analyze_count,
            "avg_latency_ms": avg_latency or 0.0
        }

@app.get("/entities/breakdown")
async def entities_breakdown():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT entity_type, COUNT(*) as count FROM event_entities GROUP BY entity_type ORDER BY count DESC")
        return [dict(row) for row in cursor.fetchall()]

@app.get("/events/recent")
async def recent_events(limit: int = 50):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE type='analyze' ORDER BY created_at DESC LIMIT ?", (limit,))
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
        return {"status": "ignored", "reason": "unsupported_label"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO labels (event_id, entity_type, label, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            event_id,
            payload.entity_type,
            payload.label,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ))
        conn.commit()
    return {"status": "ok"}

@app.get("/events/{event_id}/labels")
async def event_labels(event_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, event_id, entity_type, label, created_at
            FROM labels
            WHERE event_id = ?
            ORDER BY created_at DESC, id DESC
        """, (event_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.get("/evaluation/summary")
async def evaluation_summary():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT label, COUNT(*) as count FROM labels GROUP BY label")
        counts = {row["label"]: row["count"] for row in cursor.fetchall()}
        
        tp = counts.get("correct", 0)
        fp = counts.get("false_positive", 0)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        return {
            "tp": tp,
            "fp": fp,
            "fn": None,
            "precision": round(precision, 4),
            "recall": None,
            "f2_score": None
        }
