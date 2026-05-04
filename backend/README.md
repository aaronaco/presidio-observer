# Presidio Observer Backend

The backend is the local collection and query layer for Presidio Observer.

It receives privacy-safe analyzer events from the SDK, stores them in SQLite, and exposes the data needed by the dashboard and evaluation workflow. It is intentionally small: FastAPI for the API surface and SQLite for local persistence.

## Role in the project

The backend answers the question: "What has the analyzer been doing, and how are humans labeling those results?"

It stores metadata about analyzer calls, detected entities, latency, confidence flags, and evaluation labels. It does not store the source text or redacted output.

## Stored data

The backend stores analyzer-level metadata such as:

- event ID and correlation ID
- analyzer latency
- language
- requested entity types
- score threshold
- allow-list count
- detected entity count
- confidence flag
- NLP engine and context enhancer class names

It also stores entity-level metadata such as:

- entity type
- score
- start offset
- end offset
- span length
- recognizer name
- selected recognizer explanation metadata

For human evaluation, it stores labels as current state rather than an append-only audit trail. Repeated labels replace the previous label for the same event/entity identity so metrics do not inflate from duplicate clicks.

## Privacy boundary

The backend should never receive or persist raw text. It also should not persist anonymized text, detected values, missed values, context words, regex patterns, tokens, lemmas, or allow-list values.

Offsets and span lengths are allowed because they let the system distinguish detections without reconstructing the original content.

## Evaluation data

The backend supports three label types:

- `correct` for detections that are valid.
- `false_positive` for detections that should not have been flagged.
- `missed` for manually reported false negatives by entity type and count.

Detected labels may include entity offsets so a label can refer to a specific detection span. Missed labels intentionally do not include offsets because the analyzer did not return a span.

## API shape

The API is organized around local dashboard use:

- ingest analyzer events
- list recent analyzer events
- summarize analyzer stats
- read labels for a selected event
- write human labels
- summarize evaluation metrics

The endpoints are implementation details while the project is still evolving. Stable setup and API usage documentation will be added later.

## Development direction

The backend should stay boring and reliable. The important constraints are privacy, additive schema evolution, explicit event validation, and predictable metric behavior.
