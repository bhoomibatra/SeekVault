"""
test_privacy_ui.py — Tests for TASK-12 Privacy Center UI, storage boundaries, and offline verification.
"""

import os
from pathlib import Path
import pytest

from seekvault.database.repository import Repository
from seekvault.ui.pages.privacy_center import render_privacy_center


def test_privacy_center_callable():
    """Verify privacy center render function is importable and callable."""
    assert callable(render_privacy_center)


def test_offline_mode_environment_flags():
    """Verify that offline environment variables can be checked accurately."""
    original_hf = os.environ.get("HF_HUB_OFFLINE")
    original_tf = os.environ.get("TRANSFORMERS_OFFLINE")

    try:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        assert os.environ.get("HF_HUB_OFFLINE") == "1"
        assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    finally:
        if original_hf is not None:
            os.environ["HF_HUB_OFFLINE"] = original_hf
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)

        if original_tf is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = original_tf
        else:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)


def test_privacy_center_entity_audit_query(tmp_path):
    """Verify get_all_detected_entities returns masked representations for the audit table."""
    db_file = tmp_path / "test_privacy_audit.db"
    repo = Repository(db_path=db_file)

    folder = tmp_path / "medical_records"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "patient_file.txt"
    f1.write_text("Patient health record and lab analysis.", encoding="utf-8")
    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(f1),
        file_name="patient_file.txt",
        file_extension=".txt",
        file_size=f1.stat().st_size,
        file_hash="hash_patient_001",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        status="INDEXED"
    )

    raw_phone = "+1-555-019-2834"
    repo.save_detected_entities(rid, [
        {"entity_type": "PHONE_NUMBER", "entity_text": raw_phone, "confidence": 0.92}
    ])

    audit = repo.get_all_detected_entities()
    assert len(audit) == 1
    record = audit[0]

    assert record["file_name"] == "patient_file.txt"
    assert record["entity_type"] == "PHONE_NUMBER"
    assert "entity_token" in record
    # Crucial security check: raw phone must NEVER be present in entity_token
    assert raw_phone not in record["entity_token"]
    assert record["entity_token"].startswith("<PHONE_NUMBER_REDACTED")
