# Technology Stack and Selection Rationale

## Recommended stack

| Concern | Selection | Why it fits |
|---|---|---|
| Frontend | React.js + Vite | Component-based UI and fast development workflow |
| Backend | Python + FastAPI | Python AI ecosystem, typed APIs, validation, OpenAPI |
| Relational database | PostgreSQL | Reliable structured storage and relational integrity |
| Vector database | Qdrant | Similarity search with metadata payload filters |
| Embeddings | Sentence Transformers, `all-MiniLM-L6-v2` | Lightweight baseline for semantic retrieval experiments |
| LLM | Google Gemini API | Natural-language interpretation and structured reasoning |
| Orchestration | LangGraph | Explicit stateful graph and conditional workflow control |
| Data handling | Pandas, NumPy | Dataset profiling and transformations |
| Parsing | PyMuPDF, `python-docx`, Python standard library | Extract content from planned file formats |
| ORM / validation | SQLAlchemy, Pydantic | Database mapping and typed contracts |
| Testing | Pytest | Unit and integration testing |
| API testing | Postman | Manual endpoint validation |
| API docs | OpenAPI / Swagger UI | Inspectable API contract |
| Packaging | Docker / Docker Compose | Repeatable local environment |
| Version control | Git / GitHub | Source control and review |

## Model configuration

### Embedding model
Initial baseline: `sentence-transformers/all-MiniLM-L6-v2`.

- Use the same model and preprocessing configuration for indexing and query embedding.
- Record model name, revision, vector dimension, and distance metric in collection metadata/configuration.
- Evaluate against alternatives only if retrieval results justify the added complexity.

### LLM
Google Gemini API is the proposed language model provider.

- Keep API keys in environment variables or a secrets manager.
- Use structured output schemas where supported.
- Set bounded timeouts and retries.
- Record model identifier and prompt version for reproducibility.
- Avoid sending unnecessary personal or confidential information to the model.

## Vector collection design

Proposed Qdrant collection: `historical_defect_chunks`.

Payload fields:
- `defect_id`
- `source_project`
- `source_name`
- `source_url`
- `chunk_type`
- `chunk_index`
- `dataset_version`
- `embedding_model`

Use cosine similarity if configured consistently with the embedding model and vector normalization. Confirm the vector dimension from the actual model at collection creation rather than hard-coding an unverified value.

## Configuration principles

- Use `.env` locally and `.env.example` for documented variable names only.
- Never commit real API keys, passwords, tokens, or private dataset files.
- Pin dependency versions in the implementation environment.
- Keep model names, database URLs, collection names, upload limits, and top-k values configurable.
- Record configuration changes that affect embedding compatibility; re-index if the embedding model or preprocessing changes.
