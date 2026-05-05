# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-05

### Added
- **SDK**: Initial implementation of zero-config monkey patching for `presidio-analyzer`.
- **SDK**: Background event emitter with in-memory queue and batch flushing.
- **SDK**: Robust metadata capture including `nlp_engine`, `context_enhancer`, and `correlation_id`.
- **Backend**: FastAPI ingestion layer with SQLite persistence and schema auto-migration.
- **Backend**: Support for span-based labeling and reported missed entity counts.
- **Frontend**: Professional dashboard built with Preact and Carbon Design System.
- **Frontend**: Real-time evaluation metrics including Precision, Recall, and F2 scores.
- **Documentation**: Comprehensive README with usage examples, architecture details, and project roadmap.
- **Deployment**: Single-command orchestration via Docker Compose.

### Privacy Boundary
- Strict metadata-only capture policy: no raw text, anonymized text, or detected values are ever stored or emitted.
