# Milestone 1 — Foundation & Bug Understanding

## M1.1 — Research & Technical Understanding

Deliverables:
- Defect-analysis workflow notes.
- RAG indexing and query pipeline explanation.
- Embedding and semantic similarity study.
- Bug report structure analysis across candidate datasets.
- Technology selection rationale.

Completion evidence:
- Research notes are committed.
- Dataset sources and provenance are documented.
- Technical decisions include assumptions and limitations.

## M1.2 — System Architecture

Deliverables:
- High-level architecture diagram.
- Offline and online data-flow diagrams.
- Five agent responsibility definitions.
- Agent input/output contracts and orchestration graph.
- Canonical bug and historical defect schemas.

Completion evidence:
- Diagram and documentation agree.
- Component boundaries and storage responsibilities are clear.
- Future implementation work can be assigned to modules.

## M1.3 — Bug Submission Module

Planned functionality:
- Direct text submission.
- File upload for supported formats.
- Input and file validation.
- Text extraction and normalization.
- PostgreSQL persistence and submission status.

Completion evidence:
- Valid submissions are stored.
- Invalid files and malformed requests receive clear errors.
- Original input is retained separately from normalized content.

## M1.4 — Historical Defect Knowledge Base

Planned functionality:
- Source dataset inspection and provenance recording.
- Canonical schema mapping and cleaning.
- Structure-aware chunking.
- Embedding generation.
- Qdrant indexing with source metadata.
- Semantic retrieval tests.

Completion evidence:
- A reproducible ingestion process exists.
- Indexed chunks can be traced to original issues.
- Retrieval results are evaluated using a reviewed query set.

## Scope discipline

This milestone establishes the technical foundation. Do not claim a complete multi-agent diagnosis engine, verified root-cause detection, or automated code repair unless those capabilities are implemented and tested in a later milestone.
