# Database and Data Model

## 1. Storage responsibilities

**PostgreSQL** is the source of truth for structured reports, source defect metadata, ingestion runs, and analysis results.

**Qdrant** stores embedding vectors with metadata payloads that identify the original defect and chunk. The vector store is an index, not the only copy of the historical record.

## 2. Proposed relational entities

### `bug_reports`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `title` | VARCHAR | Required |
| `description` | TEXT | Required |
| `steps_to_reproduce` | TEXT | Nullable |
| `expected_behavior` | TEXT | Nullable |
| `actual_behavior` | TEXT | Nullable |
| `stack_trace` | TEXT | Nullable |
| `logs` | TEXT | Nullable |
| `environment` | JSONB | Structured environment details |
| `severity` | VARCHAR | Nullable until classified |
| `source_type` | VARCHAR | `paste` or `upload` |
| `status` | VARCHAR | Processing lifecycle |
| `created_at` | TIMESTAMPTZ | Creation timestamp |

### `bug_attachments`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `bug_id` | UUID | Foreign key to `bug_reports.id` |
| `original_filename` | VARCHAR | Untrusted display name |
| `stored_filename` | VARCHAR | Server-generated name |
| `media_type` | VARCHAR | Detected content type |
| `size_bytes` | BIGINT | File size |
| `storage_key` | TEXT | Private storage reference |
| `created_at` | TIMESTAMPTZ | Upload timestamp |

### `historical_defects`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Internal primary key |
| `source_project` | VARCHAR | Mozilla / Apache / Eclipse project |
| `source_defect_id` | VARCHAR | Original issue ID |
| `source_url` | TEXT | Original issue URL, if available |
| `title` | TEXT | Original title |
| `description` | TEXT | Normalized description |
| `comments` | JSONB | Optional comments |
| `resolution` | TEXT | Nullable |
| `source_status` | VARCHAR | Nullable |
| `provenance` | JSONB | Dataset/version/license/access metadata |
| `created_at_source` | TIMESTAMPTZ | Nullable |
| `updated_at_source` | TIMESTAMPTZ | Nullable |

Unique constraint candidate: `(source_project, source_defect_id)`.

### `defect_chunks`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `historical_defect_id` | UUID | Foreign key |
| `chunk_type` | VARCHAR | Description / stack trace / comment / resolution |
| `chunk_index` | INTEGER | Position within defect |
| `content` | TEXT | Chunk text |
| `token_count` | INTEGER | Approximate token count |
| `qdrant_point_id` | VARCHAR | Vector index reference |
| `embedding_model` | VARCHAR | Model identifier |
| `created_at` | TIMESTAMPTZ | Indexing timestamp |

### `analysis_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `bug_id` | UUID | Foreign key |
| `status` | VARCHAR | Pending / running / completed / failed |
| `workflow_version` | VARCHAR | Graph version |
| `model_id` | VARCHAR | LLM identifier |
| `started_at` | TIMESTAMPTZ | Nullable |
| `completed_at` | TIMESTAMPTZ | Nullable |
| `error_code` | VARCHAR | Nullable |

### `agent_results`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `analysis_run_id` | UUID | Foreign key |
| `agent_name` | VARCHAR | Agent identifier |
| `status` | VARCHAR | Completed / failed / skipped |
| `output` | JSONB | Schema-validated output |
| `duration_ms` | BIGINT | Nullable |
| `created_at` | TIMESTAMPTZ | Creation timestamp |

## 3. Qdrant payload

Each point should include:
- `defect_id`
- `source_project`
- `source_defect_id`
- `source_url`
- `chunk_type`
- `chunk_index`
- `dataset_version`
- `embedding_model`

## 4. Relationship summary

- One bug report can have multiple attachments.
- One bug report can have multiple analysis runs.
- One analysis run can have multiple agent results.
- One historical defect can have multiple chunks.
- Each vector point maps back to one chunk and one historical defect.
