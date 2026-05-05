# Presidio Observer SDK

The SDK is the instrumentation layer for Presidio Observer.

It is a small Python package that observes Presidio Analyzer calls and emits privacy-safe metadata to the local backend. It is designed for applications, agents, proxies, or GenAI redaction flows that already use Presidio and need visibility into analyzer behavior without storing analyzed text.

## Role

The SDK answers the question: "What did Presidio Analyzer detect while the application was running?"

It observes analyzer calls and emits metadata about the call and its returned entities. The backend and dashboard then make that metadata inspectable.

## Instrumentation Approach

The SDK patches `AnalyzerEngine.analyze()` at runtime. The patch is intended to be:

- idempotent, so repeated initialization does not double-wrap Presidio
- non-intrusive, so positional and keyword arguments are forwarded unchanged
- non-blocking, so event emission happens through a background queue
- optional, so applications can continue using Presidio normally

The SDK does not patch or track Presidio anonymization calls. Applications can still anonymize or redact text, but Observer currently focuses on analyzer behavior and does not capture anonymized output.

## Captured Metadata

The SDK emits metadata such as:

- event ID
- correlation ID
- latency
- language
- requested entity types
- score threshold
- allow-list count
- entity count
- detected entity types
- scores
- start and end offsets
- span lengths
- recognizer metadata
- NLP engine class
- context enhancer class

This gives enough signal to inspect behavior and compare runs without storing sensitive values.

## Privacy Boundary

The SDK must not emit:

- raw text
- anonymized text
- detected entity values
- missed entity values
- context words
- tokens or lemmas
- raw NLP artifacts
- regex patterns
- allow-list values

This boundary is the main design constraint of the package.

## Runtime Behavior

Events are queued in memory and flushed in batches. The queue is bounded so instrumentation does not block the host application indefinitely. If the queue is full, events are dropped and the drop count is available through SDK metrics.

The emitter tracks lightweight counters:

- `dropped_events`
- `failed_flushes`
- `sent_events`

Retrieve counters from application code:

```python
import presidio_observer

print(presidio_observer.metrics())
```

## Install From GitHub

Install the SDK directly from the repository:

```bash
pip install "git+https://github.com/aaronaco/presidio-observer.git#subdirectory=sdk"
```

This keeps distribution lightweight and avoids requiring a package-manager release.

## Local Development

Install SDK dependencies:

```bash
poetry install
```

Run a syntax check:

```bash
python -m py_compile presidio_observer/__init__.py presidio_observer/emitter.py presidio_observer/patcher.py
```

## Basic Usage Shape

Initialize Observer before constructing Presidio analyzer instances:

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

The host application receives normal Presidio results. Observer emits metadata about the analyzer call in the background.

For redaction flows, keep anonymization in the application:

```python
import presidio_observer
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

presidio_observer.init("http://localhost:8000")

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

user_input = "My name is Jane Doe and my phone number is 212-555-1212."
analyzer_results = analyzer.analyze(text=user_input, language="en")
redacted_text = anonymizer.anonymize(
    text=user_input,
    analyzer_results=analyzer_results,
).text

# Send redacted_text to an LLM, proxy, agent, or downstream service.
```

Observer tracks `AnalyzerEngine.analyze()` metadata only. It does not track `AnonymizerEngine.anonymize()` calls or store `redacted_text`.

## Contributing

SDK changes should preserve Presidio API compatibility. Patched methods should forward positional and keyword arguments unchanged, avoid changing analyzer return values, and never make Observer emission part of the critical path.

Useful checks:

```bash
python -m py_compile presidio_observer/__init__.py presidio_observer/emitter.py presidio_observer/patcher.py
```

Automated tests are handled after manual verification in the current project workflow.

