# Research and Technical Approach

## 1. Defect-analysis workflow

A typical defect-analysis workflow includes:
1. Intake and validation of the report.
2. Reproduction-context and environment review.
3. Classification and prioritization.
4. Stack-trace and log inspection.
5. Search for related or duplicate issues.
6. Root-cause investigation.
7. Fix proposal and regression validation.
8. Documentation and closure.

The proposed system focuses on assisting with intake, classification, evidence retrieval, analysis, and recommendation. Reproduction and final fix verification remain engineering responsibilities unless a later milestone explicitly expands scope.

## 2. RAG architecture

Retrieval-Augmented Generation combines a retrieval stage with a generation/reasoning stage.

**Indexing path**
- Normalize historical issue records.
- Split records into semantically meaningful chunks.
- Generate dense vector embeddings.
- Store vectors and metadata in Qdrant.

**Query path**
- Normalize a newly submitted defect.
- Generate a query embedding using the same embedding model.
- Retrieve top-k candidate chunks.
- Group chunks by source defect and apply metadata filters.
- Supply relevant evidence to the LLM/agents.
- Return findings with source references.

RAG reduces dependence on model parametric knowledge for project-specific historical context, but it does not guarantee factual correctness. Retrieved evidence must be checked for relevance and provenance.

## 3. Semantic similarity

Semantic similarity estimates how closely two text representations relate in embedding space. It can retrieve related reports even when they use different wording.

For normalized vectors, cosine similarity is commonly expressed as:

`cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)`

A high similarity score is a retrieval signal, not proof of a duplicate. Duplicate assessment should also compare error signatures, affected components, versions, reproduction steps, and contradictory details.

## 4. Embedding strategy

Initial baseline: `sentence-transformers/all-MiniLM-L6-v2`.

- Generate embeddings for every indexed chunk.
- Generate query vectors with the exact same model and preprocessing.
- Record model revision and vector dimension.
- Batch embedding generation for offline ingestion.
- Re-index when model or preprocessing changes.

The baseline should be evaluated on the actual defect corpus. Model selection should be based on retrieval quality, latency, memory use, and deployment constraints rather than assumed superiority.

## 5. Dataset inspection and normalization

Candidate sources:
- Mozilla defect/issue records.
- Apache project issue records.
- Eclipse defect/issue records.
- Kaggle-hosted datasets only after checking their original source and license.

For each dataset, inspect:
- Issue identifier and project.
- Title and description.
- Status and resolution.
- Comments or discussion.
- Stack traces, attachments, and environment fields where present.
- Timestamps and source URLs.

Create a source-to-canonical-field mapping before combining datasets. Missing values should remain missing rather than being fabricated.

## 6. Chunking approach

Use structure-aware chunking:
- Keep short title/description records together.
- Split long descriptions on paragraph boundaries.
- Preserve exception headers and related stack frames.
- Chunk comments by coherent comment units.
- Keep resolution text connected to its explanatory context.
- Attach original defect ID, source project, chunk type, and source URL to every chunk.

Initial tuning range: 400–700 tokens with 50–100 tokens overlap for long narrative text. These values are experimental starting points and should be adjusted based on retrieval results.

## 7. Evaluation plan

Prepare a held-out set of defect queries and have relevant historical issues reviewed manually.

Measure:
- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)
- Duplicate classification precision, recall, and F1 when labels are available
- Evidence traceability
- Retrieval latency

Record dataset version, query set, model version, chunk settings, top-k, and evaluation date. Do not report performance metrics until experiments have actually been completed.

## 8. Research log template

For each source or experiment, record:
- Question / hypothesis
- Dataset and version
- Method and configuration
- Observations
- Limitations
- Decision and rationale
- Follow-up experiment
