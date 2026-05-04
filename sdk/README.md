# Presidio Observer SDK

The SDK is the instrumentation layer for Presidio Observer.

It is a small Python package that observes Presidio Analyzer calls and emits privacy-safe metadata to the local backend. It is designed for developers who already use Presidio in an application, agent, proxy, or GenAI redaction flow and want visibility into analyzer behavior without storing the text being analyzed.

## Role in the project

The SDK answers the question: "What did Presidio Analyzer detect while my application was running?"

It observes analyzer calls and emits metadata about the call and its returned entities. The backend and dashboard then make that metadata inspectable.

## Instrumentation approach

The SDK patches `AnalyzerEngine.analyze()` at runtime. The patch is intended to be:

- idempotent, so repeated initialization does not double-wrap Presidio
- non-intrusive, so positional and keyword arguments are forwarded unchanged
- non-blocking, so event emission happens through a background queue
- optional, so applications can continue using Presidio normally

The SDK does not patch or track Presidio anonymization calls. Applications can still anonymize or redact text, but Observer currently focuses on analyzer behavior and does not capture anonymized output.

## Captured metadata

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

## Privacy boundary

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

## Why analyzer-first

In GenAI and agentic AI systems, Presidio often sits before an LLM request to identify PII that should be masked or otherwise handled. Observing the analyzer step gives developers useful signals before any model call happens:

- what would be redacted
- why certain entities were detected
- whether thresholds are too loose or too strict
- whether recognizer changes are causing false positives or misses
- how much latency the detection step adds

Anonymization remains important to the application, but Observer does not need to store anonymized output to make analyzer quality visible.

## Current status

The SDK is still evolving. Stable installation and integration instructions will be documented once the project is ready for that phase.
