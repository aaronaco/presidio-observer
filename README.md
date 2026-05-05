# Presidio Observer

Presidio Observer is a local developer tool for understanding how Microsoft Presidio behaves inside real GenAI and agentic AI workflows.

The project started from a practical gap: when Presidio is used in front of LLM calls, proxies, agents, or redaction pipelines, it can be hard to answer basic engineering questions later:

- What entity types did the analyzer detect?
- Which recognizers were involved?
- How confident were the detections?
- What did the analyzer miss?
- Are false positives increasing after a recognizer or threshold change?
- How much latency does the privacy layer add?

Presidio Observer makes those questions visible without storing the original text.

## Why this exists

A common GenAI privacy pattern is to place Presidio before an LLM request so sensitive values can be detected and masked before they reach a model provider. Microsoft documents this kind of flow in its [LiteLLM proxy sample](https://microsoft.github.io/presidio/samples/docker/litellm/), where an app talks to a proxy that applies Presidio PII masking before forwarding the request to an LLM provider.

That pattern protects the request path, but it does not automatically give developers a clear feedback loop about the redaction process itself. Presidio Observer focuses on that feedback loop.

It is not a hosted product, sales dashboard, or compliance platform. It is a local tool for developers building privacy-aware AI systems who want to inspect analyzer behavior, review detections, and collect lightweight evaluation labels while working with realistic traffic.

The same pattern can be instrumented without changing how Presidio is used:

```python
import presidio_observer
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

presidio_observer.init("http://localhost:8000")

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


def redact_before_model_call(text: str) -> str:
    analyzer_results = analyzer.analyze(text=text, language="en")
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=analyzer_results,
    )
    return anonymized.text


redacted_prompt = redact_before_model_call(
    "My name is Jane Doe and my phone number is 212-555-1212."
)

# Send only the redacted prompt to an LLM, agent, gateway, or proxy.
```

Observer records metadata about the `analyze()` call and its returned entities. It does not record the prompt, detected values, or anonymized output.

## What It Observes

Presidio Observer currently observes analyzer activity, not raw text and not anonymized output.

It records privacy-safe metadata such as:

- analyzer event IDs and correlation IDs
- latency
- language
- requested entity types
- score thresholds
- allow-list counts, without allow-list values
- detected entity types
- detection scores
- start and end offsets
- span lengths
- recognizer metadata
- confidence flags
- human evaluation labels

The intent is to show how the analyzer behaved without capturing the sensitive content that passed through it.

## What It Does Not Store

The project is intentionally strict about what it avoids:

- no raw input text
- no anonymized or redacted text
- no detected values
- no missed values
- no context words
- no tokens, lemmas, or NLP artifacts
- no regex patterns from recognizers
- no allow-list values

Offsets and span lengths are stored because they help distinguish detections without storing the text itself.

## Architecture

The project has three main parts:

- `sdk/`: Python SDK that instruments Presidio Analyzer calls and emits metadata in the background.
- `backend/`: FastAPI and SQLite service that receives events, stores metadata, and exposes dashboard/evaluation APIs.
- `frontend/`: Preact, Vite, and Carbon dashboard for inspecting analyzer events, entity metadata, latency, confidence flags, filters, auto-refresh, and human labels.

The SDK is designed to be non-blocking. Events are queued and sent in batches so observation does not sit directly on the critical path of the application using Presidio.

## Evaluation Model

Presidio returns detections. It does not know by itself whether a detection is correct, a false positive, or whether something was missed. Presidio Observer adds a simple human review layer on top of analyzer output:

- `correct`: a detected entity was useful and expected.
- `false_positive`: a detected entity should not have been flagged.
- `missed`: the analyzer failed to detect one or more entities of a given type.

Missed reports are intentionally constrained. The UI only asks for entity type and count. It does not ask for the missed text, value, or span.

Reported recall and F2 are based on manual missed counts, not an independent ground-truth dataset.

## Usage

Run the local backend and dashboard:

```bash
git clone https://github.com/aaronaco/presidio-observer.git
cd presidio-observer
docker compose up --build
```

Default local URLs:

- Frontend dashboard: `http://localhost:5173`
- Backend API: `http://localhost:8000`

### SDK From GitHub

Install the SDK directly from the repository:

```bash
pip install "git+https://github.com/aaronaco/presidio-observer.git#subdirectory=sdk"
```

Initialize the SDK before creating Presidio analyzer instances:

```python
import presidio_observer

presidio_observer.init("http://localhost:8000")
```

The host application can continue using Presidio normally after initialization.

### Basic Presidio Analyzer Usage

```python
import presidio_observer
from presidio_analyzer import AnalyzerEngine

presidio_observer.init("http://localhost:8000")

analyzer = AnalyzerEngine()
results = analyzer.analyze(
    text="Contact me at 212-555-1212.",
    language="en",
    entities=["PHONE_NUMBER"],
)

print(results)
```

The application still receives normal Presidio analyzer results. Observer receives a background event containing privacy-safe metadata such as entity type, score, offsets, span length, latency, language, and recognizer metadata.

### GenAI Redaction Flow

For LLM, agent, gateway, RAG, or proxy flows, initialize Observer once and keep the existing Presidio analyze-and-anonymize flow:

```python
import presidio_observer
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

presidio_observer.init("http://localhost:8000")

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


def prepare_prompt_for_model(user_input: str) -> str:
    analyzer_results = analyzer.analyze(text=user_input, language="en")
    anonymized = anonymizer.anonymize(
        text=user_input,
        analyzer_results=analyzer_results,
    )
    return anonymized.text


safe_prompt = prepare_prompt_for_model("Jane Doe lives at 1 Main Street.")

# Example handoff points:
# - LiteLLM or another LLM proxy
# - direct model SDK call
# - agent tool input
# - RAG query rewrite or retrieval step
```

Only the analyzer call is observed. Anonymization remains part of the application flow, but Observer does not track anonymizer calls or store redacted text.

### SDK Health Counters

```python
import presidio_observer

print(presidio_observer.metrics())
```

The counters expose dropped, failed, and sent events from the non-blocking emitter.

## Local Development

Prerequisites:

- Docker and Docker Compose
- Python 3.9 for backend/SDK work
- Poetry 2.x for Python dependency management
- Node.js 20.x and npm for frontend work

Run the full local stack:

```bash
docker compose up --build
```

Stop the Compose services:

```bash
docker compose down
```

Run the frontend directly during UI development:

```bash
cd frontend
npm install
npm run dev
```

Run the backend directly during API development:

```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

## API Overview

The backend API is local-first and supports dashboard/evaluation workflows.

Core endpoints:

- `POST /ingest`: receive analyzer events from the SDK.
- `GET /stats`: return analyzer call count and average latency.
- `GET /entities/breakdown`: return entity counts.
- `GET /events/recent`: return recent analyzer events.
- `POST /events/{event_id}/label`: save or replace a current-state evaluation label.
- `GET /events/{event_id}/labels`: list labels for an event.
- `DELETE /events/{event_id}/labels/{label_id}`: remove a saved label.
- `GET /evaluation/summary`: return precision, reported recall, and reported F2.

Filter parameters supported by dashboard summary endpoints:

- `since`: ISO datetime. Filters events at or after the timestamp.
- `language`: exact language code, such as `en`.
- `entity_type`: exact Presidio entity type, such as `EMAIL_ADDRESS`.
- `flag`: confidence flag. Supported values are `confident`, `uncertain`, and `anomaly`.
- `limit`: only available on `GET /events/recent`; accepted range is `1` to `200`.

Example filtered request:

```bash
curl "http://localhost:8000/events/recent?limit=12&language=en&entity_type=PHONE_NUMBER&flag=confident"
```

## Contributing

Contributions should preserve the project privacy boundary. Do not add raw text capture, detected values, anonymized text, context words, regex patterns, tokens, lemmas, NLP artifacts, or allow-list values to emitted events, backend storage, logs, or UI state.

Suggested local workflow:

```bash
git status
```

Backend syntax check:

```bash
python -m py_compile backend/main.py backend/database.py
```

SDK syntax check:

```bash
python -m py_compile sdk/presidio_observer/__init__.py sdk/presidio_observer/emitter.py sdk/presidio_observer/patcher.py
```

Frontend production build check:

```bash
cd frontend
npm run build
```

Docker Compose check:

```bash
docker compose config
```

Automated tests are intentionally handled after manual verification in the current project workflow.

## Non-Goals

- This is not a replacement for Presidio.
- This is not a hosted observability product.
- This is not a compliance certification system.
- This is not an audit log of sensitive content.
- This is not intended to capture anonymized text or reconstruct user input.
