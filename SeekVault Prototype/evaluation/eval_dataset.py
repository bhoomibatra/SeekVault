"""
eval_dataset.py — Standard Diagnostic Benchmark Ground-Truth Query Dataset

Contains 15 diverse semantic queries across document modalities (PDF, DOCX, TXT)
and visual image modalities (JPG, PNG) with established ground-truth target files.
"""

from typing import List, Dict, Any

BENCHMARK_QUERIES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "query": "notes about candidate elimination algorithm",
        "modality": "DOCUMENT",
        "expected_files": ["ML_Unit3_Notes.pdf", "ML_Unit3_Notes_Copy.pdf"],
        "category": "Machine Learning"
    },
    {
        "id": 2,
        "query": "database relational normalization forms BCNF",
        "modality": "DOCUMENT",
        "expected_files": ["DBMS_Lecture_4.docx"],
        "category": "Database Systems"
    },
    {
        "id": 3,
        "query": "java concurrency threads and synchronization locks",
        "modality": "DOCUMENT",
        "expected_files": ["Java_Concurrency_Notes.txt"],
        "category": "Computer Science"
    },
    {
        "id": 4,
        "query": "version space and hypothesis pruning",
        "modality": "DOCUMENT",
        "expected_files": ["ML_Unit3_Notes.pdf", "ML_Unit3_Notes_Copy.pdf"],
        "category": "Machine Learning"
    },
    {
        "id": 5,
        "query": "first and second normal form table decomposition",
        "modality": "DOCUMENT",
        "expected_files": ["DBMS_Lecture_4.docx"],
        "category": "Database Systems"
    },
    {
        "id": 6,
        "query": "multithreading thread pool executor in java",
        "modality": "DOCUMENT",
        "expected_files": ["Java_Concurrency_Notes.txt"],
        "category": "Computer Science"
    },
    {
        "id": 7,
        "query": "red car parked near a building",
        "modality": "IMAGE",
        "expected_files": ["car_parked.jpg"],
        "category": "Visual Object"
    },
    {
        "id": 8,
        "query": "screenshot showing java error or stack trace",
        "modality": "IMAGE",
        "expected_files": ["java_error_screenshot.png"],
        "category": "Visual Text/Error"
    },
    {
        "id": 9,
        "query": "students sitting in classroom during lecture",
        "modality": "IMAGE",
        "expected_files": ["classroom_lecture.jpg"],
        "category": "Visual Scene"
    },
    {
        "id": 10,
        "query": "automobile vehicle parked on pavement",
        "modality": "IMAGE",
        "expected_files": ["car_parked.jpg"],
        "category": "Visual Object"
    },
    {
        "id": 11,
        "query": "project report preliminary draft methodology",
        "modality": "DOCUMENT",
        "expected_files": ["Project_Report_Draft_v1.docx", "Project_Report_Draft_v2.docx"],
        "category": "Project Reports"
    },
    {
        "id": 12,
        "query": "final evaluation and conclusions of project",
        "modality": "DOCUMENT",
        "expected_files": ["Project_Report_Draft_v2.docx", "Project_Report_Draft_v1.docx"],
        "category": "Project Reports"
    },
    {
        "id": 13,
        "query": "student admission registration personal form",
        "modality": "DOCUMENT",
        "expected_files": ["Student_Admission_Form.pdf"],
        "category": "Personal/PII"
    },
    {
        "id": 14,
        "query": "master password secret credentials",
        "modality": "DOCUMENT",
        "expected_files": ["Master_Password_Vault.txt"],
        "category": "Security"
    },
    {
        "id": 15,
        "query": "terminal compiler null pointer exception error",
        "modality": "IMAGE",
        "expected_files": ["java_error_screenshot.png"],
        "category": "Visual Text/Error"
    }
]
