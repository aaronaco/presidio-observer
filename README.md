# Presidio Observer

Presidio Observer is a local developer tool for understanding how Microsoft Presidio behaves inside real GenAI and agentic AI workflows.

The project started from a practical gap: when Presidio is used in front of LLM calls, proxies, agents, or redaction pipelines, it can be hard to answer basic engineering questions later:

- What entity types did the analyzer detect?
- Which recognizers were involved?
- How confident were the detections?
- What did the analyzer miss?
- Are false positives increasing after a recognizer or threshold change?
- How much latency does the privacy layer add?

Presidio Observer is meant to make those questions visible without storing the original text.

## Why this exists

A common GenAI privacy pattern is to place Presidio before an LLM request so sensitive values can be detected and masked before they reach a model provider. Microsoft documents this kind of flow with LiteLLM, where an app talks to a proxy that applies Presidio PII masking before forwarding the request to an LLM provider.

That pattern protects the request path, but it does not automatically give developers a clear feedback loop about the redaction process itself. Presidio Observer focuses on that feedback loop.

It is not a hosted product, sales dashboard, or compliance platform. It is a local tool for developers building privacy-aware AI systems who want to inspect analyzer behavior, review detections, and collect lightweight evaluation labels while working with realistic traffic.

## What it observes

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

## What it does not store

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

## How the pieces fit together

The project has three main parts:

- `sdk/`: a small Python SDK that instruments Presidio Analyzer calls and emits metadata in the background.
- `backend/`: a local FastAPI and SQLite service that receives events, stores metadata, and exposes dashboard/evaluation APIs.
- `frontend/`: a Preact and Carbon dashboard for inspecting analyzer events, entity metadata, latency, confidence flags, and human labels.

The SDK is designed to be non-blocking. Events are queued and sent in batches so observation does not sit directly on the critical path of the application using Presidio.

## Evaluation model

Presidio returns detections. It does not know by itself whether a detection is correct, a false positive, or whether something was missed. Presidio Observer adds a simple human review layer on top of analyzer output:

- `correct`: a detected entity was useful and expected.
- `false_positive`: a detected entity should not have been flagged.
- `missed`: the analyzer failed to detect one or more entities of a given type.

Missed reports are intentionally constrained. The UI only asks for entity type and count. It does not ask for the missed text, value, or span.

This makes the metrics useful for local iteration while keeping the privacy boundary clear. Reported recall and F2 are based on manual missed counts, not an independent ground-truth dataset.

## Design goals

- Keep raw text out of the observer.
- Make analyzer behavior visible during real development work.
- Support GenAI and agentic AI privacy pipelines where Presidio sits before an LLM or proxy.
- Help developers tune recognizers, thresholds, and allow-lists using real operational signals.
- Stay local-first and simple: Python SDK, FastAPI, SQLite, and a lightweight dashboard.
- Avoid changing how the application uses Presidio.

## Non-goals

- This is not a replacement for Presidio.
- This is not a hosted observability product.
- This is not a compliance certification system.
- This is not an audit log of sensitive content.
- This is not intended to capture anonymized text or reconstruct user input.

## Current status

The project is still under active development. The documentation intentionally avoids setup instructions until the implementation is more stable.
