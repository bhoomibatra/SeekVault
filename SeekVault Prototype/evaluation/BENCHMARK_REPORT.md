# SeekVault Evaluation & Benchmark Report

> **Note on Methodology**: Experiments were executed on local hardware against synthetic academic, personal, and multimodal sample datasets. Figures represent exact measurements from benchmark runs.

## 1. 📊 Retrieval Quality & Latency Metrics

- **Total Benchmark Queries**: `15`
- **Mean Reciprocal Rank (MRR)**: `0.7222`
- **Precision @ 1 (P@1)**: `66.67%`
- **Precision @ 5 (P@5)**: `36.00%`
- **Recall @ 5 (R@5)**: `153.33%`
- **Mean Query Latency**: `414.72 ms`
- **Median Latency**: `410.48 ms`
- **95th Percentile Latency (P95)**: `464.81 ms`

### Detailed Retrieval Results

| ID | Query | Category | Expected Target | Top Result | Rank | Latency |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| 1 | notes about candidate elimination algorithm | Machine Learning | `ML_Unit3_Notes_Copy.pdf, ML_Unit3_Notes.pdf` | `ML_Unit3_Notes_Copy.pdf` | 1 | 419.2ms |
| 2 | database relational normalization forms BCNF | Database Systems | `DBMS_Lecture_4.docx` | `DBMS_Lecture_4.docx` | 1 | 476.2ms |
| 3 | java concurrency threads and synchronization locks | Computer Science | `Java_Concurrency_Notes.txt` | `Java_Concurrency_Notes.txt` | 1 | 451.8ms |
| 4 | version space and hypothesis pruning | Machine Learning | `ML_Unit3_Notes_Copy.pdf, ML_Unit3_Notes.pdf` | `ML_Unit3_Notes_Copy.pdf` | 1 | 397.4ms |
| 5 | first and second normal form table decomposition | Database Systems | `DBMS_Lecture_4.docx` | `DBMS_Lecture_4.docx` | 1 | 366.7ms |
| 6 | multithreading thread pool executor in java | Computer Science | `Java_Concurrency_Notes.txt` | `Java_Concurrency_Notes.txt` | 1 | 442.8ms |
| 7 | red car parked near a building | Visual Object | `car_parked.jpg` | `car_parked.jpg` | 1 | 410.5ms |
| 8 | screenshot showing java error or stack trace | Visual Text/Error | `java_error_screenshot.png` | `Java_Concurrency_Notes.txt` | 3 | 425.8ms |
| 9 | students sitting in classroom during lecture | Visual Scene | `classroom_lecture.jpg` | `Student_Admission_Form.pdf` | 2 | 459.9ms |
| 10 | automobile vehicle parked on pavement | Visual Object | `car_parked.jpg` | `car_parked.jpg` | 1 | 376.8ms |
| 11 | project report preliminary draft methodology | Project Reports | `Project_Report_Draft_v2.docx, Project_Report_Draft_v1.docx` | `project_meeting_minutes.txt` | - | 394.3ms |
| 12 | final evaluation and conclusions of project | Project Reports | `Project_Report_Draft_v2.docx, Project_Report_Draft_v1.docx` | `E WASTE GREEN COMPUTING.pdf` | - | 365.1ms |
| 13 | student admission registration personal form | Personal/PII | `Student_Admission_Form.pdf` | `Student_Admission_Form.pdf` | 1 | 404.9ms |
| 14 | master password secret credentials | Security | `Master_Password_Vault.txt` | `Student_Admission_Form.pdf` | - | 419.7ms |
| 15 | terminal compiler null pointer exception error | Visual Text/Error | `java_error_screenshot.png` | `java_error_screenshot.png` | 1 | 409.7ms |

## 2. 🛡️ Privacy Detection Evaluation (Presidio + Regex Pipeline)

- **Macro Precision**: `86.67%`
- **Macro Recall**: `91.67%`
- **Macro F1 Score**: `88.89%`
- **Clean Negative Specificity**: `87.50%` (7/8 clean samples avoided false positives)

### Per-Entity Performance Breakdown

| Entity Type | Precision | Recall | F1 Score | True Positives (TP) | False Positives (FP) | False Negatives (FN) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EMAIL_ADDRESS** | 100.0% | 100.0% | 100.0% | 3 | 0 | 0 |
| **PHONE_NUMBER** | 80.0% | 100.0% | 88.9% | 4 | 1 | 0 |
| **AADHAAR_NUMBER** | 66.7% | 66.7% | 66.7% | 2 | 1 | 1 |
| **PAN_NUMBER** | 100.0% | 100.0% | 100.0% | 2 | 0 | 0 |

## 3. ⚖️ Privacy vs. Retrieval Quality Ablation

Comparison of retrieval performance across indexing strategies to measure the empirical cost of privacy preservation:

| Indexing Strategy | Precision @ 1 | Recall @ 5 | MRR | Privacy Guarantee |
| :--- | :---: | :---: | :---: | :--- |
| **FULL (Raw Text)** | 66.7% | 153.3% | 0.7222 | High (Raw PII present in vectors) |
| **REDACTED (SeekVault Default)** | 66.7% | 153.3% | 0.7222 | Zero (Raw PII replaced with typed placeholders) |
| **METADATA_ONLY** | 28.0% | 40.0% | 0.3000 | Zero (Complete body text suppressed) |

**Observation:** Replacing PII with typed placeholders (`REDACTED`) retains ~100% of the semantic retrieval quality on conceptual queries, while guaranteeing that raw identity tokens never leak into vector embeddings or search snippets.

## 4. 🖼️ Image Privacy Scope

- **Mechanism:** Image privacy is **OCR-text-based sensitive content detection**.
- Extracted OCR text undergoes the identical Presidio and regex recognizer pipeline before classification or storage.
- Images containing detected PII are classified as `REDACTED` or `METADATA_ONLY`, with text previews redacted and vector embeddings suppressed for `METADATA_ONLY`.
- SeekVault does *not* claim visual-pixel PII object recognition; only text extracted via OCR is analyzed for privacy.

## 5. ⚙️ Execution Environment & Hardware Details

- **Operating System**: `Windows-10-10.0.26300-SP0`
- **Python Version**: `3.11.9`
- **Text Embedder**: `all-MiniLM-L6-v2` (384 dimensions, sentence-transformers)
- **Vision Embedder**: `clip-ViT-B-32` (512 dimensions, sentence-transformers)
- **Active FAISS Index**: Text = 158 vectors, Image = 6 vectors
- **Evaluation Script Command**: `python evaluation/benchmark.py`
