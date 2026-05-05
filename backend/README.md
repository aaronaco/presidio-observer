# Presidio Observer Backend

The backend is the local collection and query layer for Presidio Observer.

It receives privacy-safe analyzer events from the SDK, stores them in SQLite, and exposes the data needed by the dashboard and evaluation workflow. It is intentionally small: FastAPI for the API surface and SQLite for local persistence.

## Role

The backend answers the question: "What has the analyzer been doing, and how are humans labeling those results?"

It stores metadata about analyzer calls, detected entities, latency, confidence flags, and evaluation labels. It does not store source text or redacted output.

## Stored Data

Analyzer-level metadata includes:

- event ID and correlation ID
- analyzer latency
- language
- requested entity types
- score threshold
- allow-list count
- detected entity count
- confidence flag
- NLP engine and context enhancer class names

Entity-level metadata includes:

- entity type
- score
- start offset
- end offset
- span length
- recognizer name
- selected recognizer explanation metadata

Human evaluation labels are current state, not an append-only audit trail. Repeated labels replace the previous label for the same event/entity identity so metrics do not inflate from duplicate clicks. Saved labels can also be removed without deleting analyzer events or metadata.

## Privacy Boundary

The backend should never receive or persist raw text. It also should not persist anonymized text, detected values, missed values, context words, regex patterns, tokens, lemmas, NLP artifacts, or allow-list values.

Backend ingestion enforces an entity metadata allowlist before storage. Offsets and span lengths are allowed because they distinguish detections without reconstructing the original content.

## API

### Ingest Analyzer Events

```text
POST /ingest
```

Receives SDK event batches. Only `analyze` events are stored. Unknown entity fields are ignored by the typed ingest models and sanitized before storage.

### Dashboard Summary

```text
GET /stats
```

Returns analyzer event count and average latency.

### Entity Breakdown

```text
GET /entities/breakdown
```

Returns entity counts grouped by entity type.

### Recent Events

```text
GET /events/recent
```

Returns recent analyzer events. `limit` defaults to `50` and accepts values from `1` to `200`.

### Event Labels

```text
GET /events/{event_id}/labels
POST /events/{event_id}/label
DELETE /events/{event_id}/labels/{label_id}
```

Detected labels support `correct` and `false_positive`. Missed labels support `missed` with entity type and count only.

Detected labels can include `entity_start` and `entity_end` so a label can refer to a specific detection span. Missed labels intentionally do not include offsets because the analyzer did not return a span.

### Evaluation Summary

```text
GET /evaluation/summary
```

Returns precision, reported recall, and reported F2 based on saved labels.

## Filter Parameters

The following query parameters are supported by `GET /stats`, `GET /entities/breakdown`, `GET /events/recent`, and `GET /evaluation/summary`:

| Parameter | Description | Example |
| --- | --- | --- |
| `since` | ISO datetime. Returns events at or after the timestamp. | `2026-05-05T00:00:00Z` |
| `language` | Exact analyzer language code. | `en` |
| `entity_type` | Exact Presidio entity type. | `PHONE_NUMBER` |
| `flag` | Confidence flag. Supported values: `confident`, `uncertain`, `anomaly`. | `confident` |

`GET /events/recent` also supports:

| Parameter | Description | Example |
| --- | --- | --- |
| `limit` | Maximum number of events. Accepted range: `1` to `200`. | `12` |

Example:

```bash
curl "http://localhost:8000/events/recent?limit=12&language=en&entity_type=PHONE_NUMBER&flag=confident"
```

## Docker Compose

Build and run the backend service through Docker Compose.

Run from the repository root:

```bash
docker compose up --build backend
```

Default URL:

```text
http://localhost:8000
```

SQLite data is stored under `data/` when running through Docker Compose.

## Local Development

Install dependencies:

```bash
poetry install
```

Run the backend locally:

```bash
poetry run uvicorn main:app --reload
```

## Contributing

Keep backend changes privacy-safe by default. API models should be explicit, ingestion should sanitize before persistence, and SQLite schema changes should be additive unless a reset/migration is planned.

Useful checks:

```bash
python -m py_compile backend/main.py backend/database.py
docker compose config
```

Automated tests are handled after manual verification in the current project workflow.

