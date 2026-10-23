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

# ---------------------------------------------------------------------------
# Labeled Privacy Detection Ground-Truth Dataset (Indian & Global PII)
# ---------------------------------------------------------------------------
PRIVACY_EVAL_DATASET: List[Dict[str, Any]] = [
    {
        "id": "p1",
        "text": "Please contact student coordinator at student.coordinator@example.com for admission queries.",
        "expected_entities": [{"type": "EMAIL_ADDRESS", "value": "student.coordinator@example.com"}]
    },
    {
        "id": "p2",
        "text": "For technical escalations write to dev-ops+infra@cloud.subdomain.org immediately.",
        "expected_entities": [{"type": "EMAIL_ADDRESS", "value": "dev-ops+infra@cloud.subdomain.org"}]
    },
    {
        "id": "p3",
        "text": "Candidate registered with mobile number +91 9876543210 for identity verification.",
        "expected_entities": [{"type": "PHONE_NUMBER", "value": "+91 9876543210"}]
    },
    {
        "id": "p4",
        "text": "Office hotline: +1 (555) 234-5678 during standard working hours.",
        "expected_entities": [{"type": "PHONE_NUMBER", "value": "+1 (555) 234-5678"}]
    },
    {
        "id": "p5",
        "text": "Direct phone number 9876543210 registered in database records.",
        "expected_entities": [{"type": "PHONE_NUMBER", "value": "9876543210"}]
    },
    {
        "id": "p6",
        "text": "Government proof submitted: Aadhaar card number 4521 8963 1254 verified by nodal officer.",
        "expected_entities": [{"type": "AADHAAR_NUMBER", "value": "4521 8963 1254"}]
    },
    {
        "id": "p7",
        "text": "Resident UID: 9876-5432-1098 presented at certificate verification counter.",
        "expected_entities": [{"type": "AADHAAR_NUMBER", "value": "9876-5432-1098"}]
    },
    {
        "id": "p8",
        "text": "Income Tax PAN details provided: ABCDE1234F for salary processing.",
        "expected_entities": [{"type": "PAN_NUMBER", "value": "ABCDE1234F"}]
    },
    {
        "id": "p9",
        "text": "Permanent Account Number BNZPK9876L recorded in tax clearance certificate.",
        "expected_entities": [{"type": "PAN_NUMBER", "value": "BNZPK9876L"}]
    },
    {
        "id": "p10",
        "text": "Combined profile: Reach Priya at priya.sharma@startup.in, phone +91 9123456789, Aadhaar 3214 5698 7412.",
        "expected_entities": [
            {"type": "EMAIL_ADDRESS", "value": "priya.sharma@startup.in"},
            {"type": "PHONE_NUMBER", "value": "+91 9123456789"},
            {"type": "AADHAAR_NUMBER", "value": "3214 5698 7412"}
        ]
    },
    # Tricky Near-Misses & Clean Negatives (Must NOT trigger False Positives)
    {
        "id": "n1",
        "text": "First Normal Form (1NF) ensures atomic column values, while BCNF removes functional anomalies.",
        "expected_entities": []
    },
    {
        "id": "n2",
        "text": "Git commit hash 4b97949a8c1f0d3e2b and SHA-256 digest b5a5ac4ff341cf.",
        "expected_entities": []
    },
    {
        "id": "n3",
        "text": "HTTP status code 404 Not Found at port 8501 on localhost 127.0.0.1.",
        "expected_entities": []
    },
    {
        "id": "n4",
        "text": "Invoice item SKU-987654 and product serial number 12345678 are non-phone numeric codes.",
        "expected_entities": []
    },
    {
        "id": "n5",
        "text": "Invalid email syntax user@ and @domain.com and mailto: should not trigger valid entity.",
        "expected_entities": []
    },
    {
        "id": "n6",
        "text": "Alphanumeric token ABCDE12345 has 5 numbers instead of 4 and is not a valid PAN.",
        "expected_entities": []
    },
    {
        "id": "n7",
        "text": "Numeric group 1234 5678 9012 3456 has 16 digits and is not a 12-digit Aadhaar.",
        "expected_entities": []
    },
    {
        "id": "n8",
        "text": "Short code 1234 5678 has only 8 digits and must not be flagged as Aadhaar.",
        "expected_entities": []
    }
]

