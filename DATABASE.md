# SeekVault Database & Vector Index Specification

## 1. Relational Database Design (SQLite 3)

SeekVault uses SQLite 3 as its local transactional relational database store. The database stores system configuration, authorized directory lists, file metadata, privacy classification logs, chunk-level vector mappings, and versioning relationships.

### Database File Path
- Default location: `~/.seekvault/seekvault.db` or `<workspace>/data/seekvault.db`

---

## 2. Entity Relationship Diagram & Schema DDL

```
  +--------------------+             +------------------------+
  | authorized_folders |             |      privacy_logs      |
  +--------------------+             +------------------------+
  | id (PK)            |             | id (PK)                |
  | folder_path        |             | file_id (FK)           |
  | is_active          |             | detected_entities_json |
  +--------------------+             | applied_tier           |
                                     +------------------------+
                                                 |
                                                 v
  +--------------------+ 1         * +------------------------+
  |      version_groups| <----------- |         files          |
  +--------------------+             +------------------------+
  | id (PK)            |             | id (PK)                |
  | canonical_file_id  |             | file_path              |
  | group_name         |             | file_name              |
  +--------------------+             | sha256_hash            |
                                     | phash                  |
                                     | privacy_tier           |
                                     | indexing_status        |
                                     | version_group_id (FK)  |
                                     +------------------------+
                                        |                  |
                       +----------------+                  +----------------+
                       | 1                                                  | 1
                       v *                                                  v *
  +-----------------------------------+                +-----------------------------------+
  |          document_chunks          |                |          image_metadata           |
  +-----------------------------------+                +-----------------------------------+
  | id (PK)                           |                | id (PK)                           |
  | file_id (FK)                      |                | file_id (FK)                      |
  | chunk_index                       |                | width, height, format             |
  | raw_text                          |                | ocr_raw_text                      |
  | redacted_text                     |                | ocr_redacted_text                 |
  | vector_faiss_id                   |                | text_vector_faiss_id              |
  +-----------------------------------+                | visual_vector_faiss_id            |
                                                       +-----------------------------------+
                                                                        |
                                                                        v
                                                       +-----------------------------------+
                                                       |        faiss_index_mapping        |
                                                       +-----------------------------------+
                                                       | faiss_vector_id (PK)              |
                                                       | index_type ('text'/'visual')      |
                                                       | entity_type ('chunk'/'image')     |
                                                       | entity_id                         |
                                                       +-----------------------------------+
```

---

### Complete SQLite DDL Schema

```sql
-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- 1. Authorized Folders Table
CREATE TABLE IF NOT EXISTS authorized_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL UNIQUE,
    is_recursive INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Version Groups Table
CREATE TABLE IF NOT EXISTS version_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_file_id INTEGER,
    group_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (canonical_file_id) REFERENCES files(id) ON DELETE SET NULL
);

-- 3. Files Metadata Table
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_extension TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    sha256_hash TEXT NOT NULL,
    phash TEXT,
    file_type TEXT CHECK(file_type IN ('document', 'image', 'other')) NOT NULL,
    privacy_tier TEXT CHECK(privacy_tier IN ('FULL', 'REDACTED', 'METADATA_ONLY')) NOT NULL DEFAULT 'FULL',
    indexing_status TEXT CHECK(indexing_status IN ('PENDING', 'INDEXED', 'FAILED', 'SKIPPED', 'DELETED')) NOT NULL DEFAULT 'PENDING',
    version_group_id INTEGER,
    is_canonical INTEGER DEFAULT 1,
    error_message TEXT,
    last_indexed_at TIMESTAMP,
    FOREIGN KEY (version_group_id) REFERENCES version_groups(id) ON DELETE SET NULL
);

-- Indexing for fast lookups
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_files_phash ON files(phash);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(indexing_status);
CREATE INDEX IF NOT EXISTS idx_files_privacy ON files(privacy_tier);

-- 4. Document Chunks Table
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER DEFAULT 1,
    start_char_idx INTEGER,
    end_char_idx INTEGER,
    raw_text TEXT,
    redacted_text TEXT,
    presidio_entities_json TEXT,
    vector_faiss_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON document_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_faiss_id ON document_chunks(vector_faiss_id);

-- 5. Image Metadata & OCR Table
CREATE TABLE IF NOT EXISTS image_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL UNIQUE,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    format TEXT NOT NULL,
    channels INTEGER,
    ocr_raw_text TEXT,
    ocr_redacted_text TEXT,
    presidio_entities_json TEXT,
    text_vector_faiss_id INTEGER,
    visual_vector_faiss_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_image_file_id ON image_metadata(file_id);
CREATE INDEX IF NOT EXISTS idx_image_visual_faiss ON image_metadata(visual_vector_faiss_id);

-- 6. FAISS Index Bidirectional Mapping Table
CREATE TABLE IF NOT EXISTS faiss_index_mapping (
    faiss_vector_id INTEGER PRIMARY KEY,
    index_type TEXT CHECK(index_type IN ('text', 'visual')) NOT NULL,
    entity_type TEXT CHECK(entity_type IN ('document_chunk', 'image_metadata')) NOT NULL,
    entity_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_faiss_mapping_entity ON faiss_index_mapping(entity_type, entity_id);

-- 7. File Versions Relationship Table
CREATE TABLE IF NOT EXISTS file_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    parent_file_id INTEGER NOT NULL,
    child_file_id INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    relation_type TEXT CHECK(relation_type IN ('exact_duplicate', 'near_duplicate', 'newer_version')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES version_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (child_file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 8. Privacy Audit Logs Table
CREATE TABLE IF NOT EXISTS privacy_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    detected_pii_types_json TEXT NOT NULL,
    sensitivity_score REAL NOT NULL,
    applied_tier TEXT CHECK(applied_tier IN ('FULL', 'REDACTED', 'METADATA_ONLY')) NOT NULL,
    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);
```

---

## 3. FAISS Index Design

SeekVault maintains two distinct FAISS vector index files on disk to separate document text embeddings from visual image embeddings.

### 1. Text Vector Index (`seekvault_text.faiss`)
- **Embedding Model**: `SentenceTransformers` (Default: `all-MiniLM-L6-v2`, Dimension = 384, or `all-mpnet-base-v2`, Dimension = 768).
- **Metric**: Inner Product / Cosine Similarity (vectors normalized to unit length prior to insertion).
- **FAISS Index Type**: `IndexIDMap2(IndexFlatIP(384))` or `IndexHNSWFlat(384, 32)` for large datasets.
- **Contents**:
  - `FULL` tier document text chunk embeddings.
  - `REDACTED` tier anonymized document text chunk embeddings.
  - OCR extracted text embeddings from `FULL`/`REDACTED` images.

### 2. Visual Vector Index (`seekvault_visual.faiss`)
- **Embedding Model**: `CLIP` (`openai/clip-vit-base-patch32`, Dimension = 512) or `SigLIP` (Dimension = 768).
- **Metric**: Inner Product / Cosine Similarity (unit L2 normalized).
- **FAISS Index Type**: `IndexIDMap2(IndexFlatIP(512))`.
- **Contents**:
  - Visual image embeddings extracted directly from image pixels via CLIP Image Encoder.

---

## 4. Vector ID Mapping & Persistence Strategy

### Dynamic ID Allocation
1. SQLite's `faiss_index_mapping` table maintains an auto-incrementing integer `faiss_vector_id`.
2. When adding a vector to FAISS, `faiss.IndexIDMap2` is used so that each vector in FAISS is explicitly tied to its `faiss_vector_id`.
3. Query Retrieval Pipeline:
   ```
   [Query] -> FAISS Search -> Returns [faiss_vector_id, score]
                  |
                  v
   [faiss_index_mapping] Table Lookup -> Returns [entity_type, entity_id, file_id]
                  |
                  v
   [files] Table Query -> Checks Folder Authorization & Retrieves File Path + Metadata
   ```

### Persistence & Serialization
- Vector index state is saved to disk whenever indexing runs or Watchdog batches complete.
- Index files:
  - `~/.seekvault/indices/seekvault_text.faiss`
  - `~/.seekvault/indices/seekvault_visual.faiss`
- On startup, SeekVault checks if `.faiss` files exist and loads them into memory. If index corruption is detected, SeekVault automatically rebuilds the FAISS index directly from text chunks stored in SQLite.

---

## 5. Incremental Index Update Strategy

1. **Addition**:
   - New file detected -> Ingest & Embed -> Allocate `faiss_vector_id` in SQLite -> Call `index.add_with_ids(vectors, ids)` -> `faiss.write_index()`.
2. **Deletion**:
   - File deleted from authorized folder -> Query SQLite for all `faiss_vector_id`s tied to `file_id` -> Call `index.remove_ids(faiss_ids)` -> Delete mappings in SQLite -> Set `files.indexing_status = 'DELETED'`.
3. **Modification**:
   - File modified -> Perform Deletion step for old `file_id` vectors -> Re-run parsing, privacy scan, and embedding -> Perform Addition step.
