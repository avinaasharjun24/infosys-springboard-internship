# System Architecture

## 1. Architectural objective

Define a modular foundation for an AI-assisted software defect analysis system. The design combines report intake, historical defect retrieval, and a specialized multi-agent workflow while keeping data ingestion separate from live analysis.

## 2. Logical components

| Component | Responsibility | Primary interface |
|---|---|---|
| React client | Capture reports, upload files, show analysis | HTTPS / JSON, multipart upload |
| FastAPI API layer | Validate requests and expose application endpoints | REST |
| Submission service | Create submission IDs and coordinate persistence | Internal Python service |
| File parser | Extract text from supported formats | Parser interface |
| Normalization service | Normalize fields while preserving technical evidence | Canonical report object |
| PostgreSQL repository | Store structured records and execution state | SQL / SQLAlchemy (proposed) |
| Ingestion pipeline | Clean, map, chunk, and embed historical defects | Batch Python job |
| Embedding service | Generate query and document embeddings | Sentence Transformers |
| Qdrant | Store vectors and metadata; return nearest neighbors | Qdrant client |
| RAG service | Build query, retrieve, group, and format evidence | Internal Python service |
| LangGraph orchestrator | Coordinate agent execution and shared state | Typed workflow state |
| Agent modules | Produce specialized structured findings | Pydantic schemas |
| Results service | Validate, persist, and return analysis | REST / PostgreSQL |

## 3. Runtime boundaries

### Offline boundary
Historical datasets are imported through a controlled batch pipeline. This pipeline is not invoked for every user submission. It writes normalized source records to PostgreSQL and vectorized chunks to Qdrant.

### Online boundary
A user submission is validated and stored. The query is embedded, relevant historical chunks are retrieved, and evidence is passed into the orchestration graph. Results are schema-validated and persisted before being returned to the client.

## 4. Architecture diagram

See `system-architecture.mmd` for the standalone Mermaid source and the root README for the rendered diagram.

## 5. Design decisions

1. **Modular monolith initially:** Keep services as clear Python modules within one backend deployment. Split into separately deployed services only when scale or operational needs justify it.
2. **PostgreSQL + Qdrant:** Use relational storage for canonical records and vector storage for semantic retrieval. Avoid duplicating the full source of truth in the vector database.
3. **Separate ingestion and query pipelines:** Make dataset processing repeatable and prevent expensive re-indexing during user requests.
4. **Evidence-first agent inputs:** Agents receive source-linked retrieved evidence and must distinguish observed facts from hypotheses.
5. **Typed agent outputs:** Define stable Pydantic contracts to make orchestration, testing, and UI rendering predictable.
6. **Human engineering review:** Recommendations are advisory. The initial system does not automatically edit repositories or apply fixes.

## 6. Proposed deployment topology

For the initial implementation, a local Docker Compose environment can run:
- React development server
- FastAPI backend
- PostgreSQL
- Qdrant

The embedding model can run in the backend process for the first prototype. Gemini is accessed through its API using a server-side secret. Raw datasets remain in a local data directory or approved storage location and are not committed by default.

## 7. Failure handling

- Parser failure: retain submission metadata, record a parse error, and return a clear status.
- Embedding failure: stop retrieval and mark the analysis as incomplete rather than fabricating evidence.
- Vector database unavailable: return a controlled retrieval-unavailable state; do not claim historical comparison was performed.
- LLM timeout/rate limit: apply bounded retries and expose a failed or partial analysis state.
- Invalid agent output: validate against schema, retry only within a configured limit, then record validation failure.
