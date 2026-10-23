# SeekVault Retrieval Quality & Latency Benchmark Report

## 📊 Executive Summary Metrics

- **Total Benchmark Queries**: `15`
- **Mean Reciprocal Rank (MRR)**: `0.7333`
- **Precision @ 1 (P@1)**: `66.67%`
- **Precision @ 5 (P@5)**: `18.67%`
- **Recall @ 5 (R@5)**: `80.00%`
- **Mean Query Latency**: `172.72 ms`
- **Median Latency**: `166.68 ms`
- **95th Percentile Latency (P95)**: `209.14 ms`

## 📋 Detailed Query Results

| ID | Query | Expected Target | Top Result | Hit Rank | MRR | Latency |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| 1 | notes about candidate elimination algorithm | `ML_Unit3_Notes_Copy.pdf, ML_Unit3_Notes.pdf` | `ML_Unit3_Notes_Copy.pdf` | 1 | 1.00 | 189.8ms |
| 2 | database relational normalization forms BCNF | `DBMS_Lecture_4.docx` | `DBMS_Lecture_4.docx` | 1 | 1.00 | 173.3ms |
| 3 | java concurrency threads and synchronization locks | `Java_Concurrency_Notes.txt` | `Java_Concurrency_Notes.txt` | 1 | 1.00 | 188.1ms |
| 4 | version space and hypothesis pruning | `ML_Unit3_Notes_Copy.pdf, ML_Unit3_Notes.pdf` | `ML_Unit3_Notes_Copy.pdf` | 1 | 1.00 | 254.2ms |
| 5 | first and second normal form table decomposition | `DBMS_Lecture_4.docx` | `DBMS_Lecture_4.docx` | 1 | 1.00 | 172.9ms |
| 6 | multithreading thread pool executor in java | `Java_Concurrency_Notes.txt` | `Java_Concurrency_Notes.txt` | 1 | 1.00 | 170.2ms |
| 7 | red car parked near a building | `car_parked.jpg` | `car_parked.jpg` | 1 | 1.00 | 150.6ms |
| 8 | screenshot showing java error or stack trace | `java_error_screenshot.png` | `Java_Concurrency_Notes.txt` | 2 | 0.50 | 161.5ms |
| 9 | students sitting in classroom during lecture | `classroom_lecture.jpg` | `Student_Admission_Form.pdf` | 2 | 0.50 | 150.3ms |
| 10 | automobile vehicle parked on pavement | `car_parked.jpg` | `car_parked.jpg` | 1 | 1.00 | 162.8ms |
| 11 | project report preliminary draft methodology | `Project_Report_Draft_v1.docx, Project_Report_Draft_v2.docx` | `project_meeting_minutes.txt` | - | 0.00 | 159.3ms |
| 12 | final evaluation and conclusions of project | `Project_Report_Draft_v1.docx, Project_Report_Draft_v2.docx` | `classroom_lecture.jpg` | - | 0.00 | 166.7ms |
| 13 | student admission registration personal form | `Student_Admission_Form.pdf` | `Student_Admission_Form.pdf` | 1 | 1.00 | 156.4ms |
| 14 | master password secret credentials | `Master_Password_Vault.txt` | `Student_Admission_Form.pdf` | - | 0.00 | 176.8ms |
| 15 | terminal compiler null pointer exception error | `java_error_screenshot.png` | `java_error_screenshot.png` | 1 | 1.00 | 157.8ms |

## ⚙️ Test Environment & Model Metadata

- **Platform**: `Windows-10-10.0.26300-SP0`
- **Python Version**: `3.11.9`
- **Text Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions, sentence-transformers)
- **Image Embedding Model**: `clip-ViT-B-32` (512 dimensions, sentence-transformers)
- **Index Size**: FAISS Text = 11 vectors, FAISS Image = 3 vectors
- **Fusion Method**: Reciprocal Rank Fusion (RRF) with SQLite FTS5
- **Evaluation Dataset**: 15 multi-domain semantic and cross-modal queries

## ⚠️ Limitations & Methodological Constraints

- Latency measurements reflect warm in-memory inference on local CPU without dedicated GPU acceleration.
- Exact duplicate documents with identical textual content will share identical semantic scores and may alternate top ranks.
- Image retrieval queries rely on zero-shot visual-semantic alignment via CLIP ViT-B/32.
- Heuristic version matching is evaluated independently as an exploratory grouping heuristic, not an authoritative VCS commit graph.
