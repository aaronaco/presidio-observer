from fastapi import FastAPI, HTTPException, Request, Query
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

@app.post("/ingest")
async def ingest_events(payload: EventPayload):
    with get_db() as conn:
        cursor = conn.cursor()
        for event in payload.events:
            entities = event.get("entities", [])
            operators_used = event.get("operators_used", [])
            
            cursor.execute("""
                INSERT INTO events (id, type, latency_ms, language, entity_count, has_pii, entities, operators_used, items_anonymized, flag, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event["id"],
                event["type"],
                event.get("latency_ms"),
                event.get("language"),
                event.get("entity_count"),
                event.get("has_pii", False),
                json.dumps(entities) if entities else None,
                json.dumps(operators_used) if operators_used else None,
                event.get("items_anonymized"),
                event.get("flag"),
                event.get("created_at")
            ))
            
            if event["type"] == "analyze":
                for ent in entities:
                    cursor.execute("""
                        INSERT INTO event_entities (event_id, entity_type, score, recognizer, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        event["id"],
                        ent.get("type"),
                        ent.get("score"),
                        ent.get("recognizer"),
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
        cursor.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,))
        events = []
        for row in cursor.fetchall():
            d = dict(row)
            if d["entities"]: d["entities"] = json.loads(d["entities"])
            if d["operators_used"]: d["operators_used"] = json.loads(d["operators_used"])
            events.append(d)
        return events

@app.post("/events/{event_id}/label")
async def label_event(event_id: str, payload: LabelPayload):
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

@app.get("/evaluation/summary")
async def evaluation_summary():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT label, COUNT(*) as count FROM labels GROUP BY label")
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
