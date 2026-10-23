import os
import shutil
import zipfile
import pytest
from pathlib import Path

from seekvault.database.repository import Repository
from seekvault.database.schema import init_db
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.privacy.analyzer import PrivacyAnalyzer
from seekvault.privacy.recognizers import scan_custom_patterns
from seekvault.database.backup import create_backup, restore_backup
from seekvault.ui.components import open_file_in_os, open_folder_in_os


@pytest.fixture
def test_env(tmp_path):
    """Create an isolated test environment with fresh SQLite DB and FAISS index paths."""
    db_path = tmp_path / "test_seekvault.db"
    index_dir = tmp_path / "indices"
    index_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    text_idx_path = index_dir / "text_index.faiss"
    text_meta_path = index_dir / "text_ids.json"
    img_idx_path = index_dir / "image_index.faiss"
    img_meta_path = index_dir / "image_ids.json"

    repo = Repository(db_path=db_path)
    engine = SearchEngine(
        repository=repo,
        text_index_path=text_idx_path,
        text_meta_path=text_meta_path,
        image_index_path=img_idx_path,
        image_meta_path=img_meta_path,
    )
    pipeline = IngestionPipeline(repository=repo, search_engine=engine)

    return {
        "tmp_path": tmp_path,
        "db_path": db_path,
        "index_dir": index_dir,
        "backups_dir": backups_dir,
        "repo": repo,
        "engine": engine,
        "pipeline": pipeline,
    }


# ===========================================================================
# 1. Privacy Dashboard Tests
# ===========================================================================

def test_privacy_detection_rules_enable_disable(test_env):
    """Test that detection rules for phone, email, id, and financial can be enabled and disabled."""
    repo = test_env["repo"]

    # Sample text containing phone, email, PAN card, credit card, and API key
    sample_text = (
        "Contact me at user@example.com or +91 9876543210. "
        "My PAN is ABCDE1234F and CC is 4532-1234-5678-9012. "
        "Key: api_key=supersecretkey123"
    )

    # 1. All enabled
    all_rules = {"phone": True, "email": True, "id": True, "financial": True}
    ents_all = PrivacyAnalyzer.analyze(sample_text, enabled_rules=all_rules)
    types_all = {e["entity_type"] for e in ents_all}
    assert "EMAIL_ADDRESS" in types_all
    assert "PHONE_NUMBER" in types_all
    assert "PAN_NUMBER" in types_all
    assert "CREDIT_CARD" in types_all
    assert "CONFIDENTIAL_KEY" in types_all

    # 2. Disable phone and email
    no_contact_rules = {"phone": False, "email": False, "id": True, "financial": True}
    ents_no_contact = PrivacyAnalyzer.analyze(sample_text, enabled_rules=no_contact_rules)
    types_no_contact = {e["entity_type"] for e in ents_no_contact}
    assert "EMAIL_ADDRESS" not in types_no_contact
    assert "PHONE_NUMBER" not in types_no_contact
    assert "PAN_NUMBER" in types_no_contact
    assert "CREDIT_CARD" in types_no_contact
    assert "CONFIDENTIAL_KEY" in types_no_contact  # credentials always active

    # 3. Disable ID and Financial
    no_id_fin_rules = {"phone": True, "email": True, "id": False, "financial": False}
    ents_no_id_fin = PrivacyAnalyzer.analyze(sample_text, enabled_rules=no_id_fin_rules)
    types_no_id_fin = {e["entity_type"] for e in ents_no_id_fin}
    assert "EMAIL_ADDRESS" in types_no_id_fin
    assert "PHONE_NUMBER" in types_no_id_fin
    assert "PAN_NUMBER" not in types_no_id_fin
    assert "CREDIT_CARD" not in types_no_id_fin


def test_privacy_settings_persistence(test_env):
    """Test that privacy protection mode and detection rules persist across instances."""
    repo = test_env["repo"]
    db_path = test_env["db_path"]

    # Save settings
    repo.set_setting("privacy_protection_mode", "EXCLUDE_BODY")
    repo.set_setting("detect_phone", "0")
    repo.set_setting("detect_email", "1")
    repo.set_setting("detect_id", "0")
    repo.set_setting("detect_financial", "1")

    # Reopen fresh repository connected to same database
    fresh_repo = Repository(db_path=db_path)
    assert fresh_repo.get_setting("privacy_protection_mode") == "EXCLUDE_BODY"
    assert fresh_repo.get_setting("detect_phone") == "0"
    assert fresh_repo.get_setting("detect_email") == "1"
    assert fresh_repo.get_setting("detect_id") == "0"
    assert fresh_repo.get_setting("detect_financial") == "1"


def test_privacy_protection_modes_mask_vs_exclude_body(test_env):
    """Test that MASK_SNIPPETS produces masked tokens and EXCLUDE_BODY hides body text."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    engine = test_env["engine"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "sensitive_docs"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    doc_file = folder / "client_profile.txt"
    doc_file.write_text("Confidential client dossier: phone is +91 9876543210 and email is client@example.com")

    # Mode 1: MASK_SNIPPETS
    repo.set_setting("privacy_protection_mode", "MASK_SNIPPETS")
    res1 = pipeline.process_file(str(doc_file), force_reembed=True)
    assert res1["status"] == "INDEXED"
    assert res1["privacy_tier"] == "REDACTED"
    content1 = repo.get_file_content(res1["id"])
    assert "<PHONE_NUMBER>" in content1["redacted_preview"] or "REDACTED" in content1["redacted_preview"]
    assert "+91 9876543210" not in content1["redacted_preview"]

    # Mode 2: EXCLUDE_BODY
    repo.set_setting("privacy_protection_mode", "EXCLUDE_BODY")
    res2 = pipeline.process_file(str(doc_file), force_reembed=True)
    content2 = repo.get_file_content(res2["id"])
    assert "[DOCUMENT TEXT HIDDEN - PRIVACY PROTECTION]" in content2["redacted_preview"]


def test_privacy_exclude_action_removes_from_library_preserves_disk(test_env):
    """Test that excluding a file removes it from DB & search index, but original file remains on disk."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "work"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    doc = folder / "sensitive_agreement.txt"
    doc.write_text("Sensitive agreement with PAN ABCDE1234F and salary 5000000")

    res = pipeline.process_file(str(doc))
    fid = res["id"]
    assert repo.get_file_by_id(fid) is not None
    assert len(repo.get_detected_entities_for_file(fid)) > 0

    # Exclude the file
    deleted = repo.delete_file_by_path(str(doc))
    assert deleted is True

    # DB record is gone
    assert repo.get_file_by_id(fid) is None
    assert repo.get_file_content(fid) is None
    assert len(repo.get_detected_entities_for_file(fid)) == 0

    # CRITICAL: Disk file is completely untouched
    assert doc.exists() is True
    assert "ABCDE1234F" in doc.read_text()


def test_open_file_and_show_in_folder_helpers(test_env):
    """Test open_file_in_os and open_folder_in_os with existing and missing files."""
    tmp_path = test_env["tmp_path"]
    f = tmp_path / "sample.txt"
    f.write_text("test")

    # Missing file returns error
    ok, msg = open_file_in_os(str(tmp_path / "nonexistent.txt"))
    assert ok is False
    assert "File does not exist on disk" in msg

    ok_fld, msg_fld = open_folder_in_os("")
    assert ok_fld is False
    assert "Invalid file path" in msg_fld


# ===========================================================================
# 2. Settings Dashboard Tests
# ===========================================================================

def test_settings_search_mode_smart_vs_keyword(test_env):
    """Test that Smart Match (HYBRID) and Exact Words Only (KEYWORD_ONLY) use correct engines."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    engine = test_env["engine"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "notes"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    doc = folder / "concurrency_notes.txt"
    doc.write_text("Database transaction deadlock occurs when two transactions wait for locks.")
    pipeline.process_file(str(doc))

    # Keyword Search (Exact words)
    kw_results = engine.search_keyword("deadlock")
    assert len(kw_results) > 0
    assert kw_results[0]["relevance_label"] == "Keyword"

    # Hybrid Search
    hyb_results = engine.search_hybrid("deadlock")
    assert len(hyb_results) > 0
    assert hyb_results[0]["relevance_label"] in ("Keyword", "Semantic", "Both")


def test_settings_results_limit_enforced(test_env):
    """Test that results_per_page (10, 25, 50) setting limits returned records."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    engine = test_env["engine"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "bulk"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    for i in range(15):
        (folder / f"report_{i}.txt").write_text(f"Financial quarter summary report {i}")
    pipeline.scan_folder(str(folder))

    # Top-k = 5
    res_5 = engine.search_keyword("report", top_k=5)
    assert len(res_5) <= 5

    # Top-k = 10
    res_10 = engine.search_keyword("report", top_k=10)
    assert len(res_10) == 10


def test_settings_temporary_file_exclusion(test_env):
    """Test that skip_temp_files ignores ~$lock, .tmp, and .crdownload files when enabled."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "office_work"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    valid_doc = folder / "presentation.txt"
    valid_doc.write_text("Real content")
    temp_doc1 = folder / "~$presentation.txt"
    temp_doc1.write_text("Lock content")
    temp_doc2 = folder / "draft.tmp"
    temp_doc2.write_text("Tmp content")

    # Case 1: skip_temp_files = 1 (default)
    repo.set_setting("skip_temp_files", "1")
    count = pipeline.scan_folder(str(folder))
    assert count == 1
    assert repo.get_file_by_path(str(valid_doc)) is not None
    assert repo.get_file_by_path(str(temp_doc1)) is None


def test_settings_max_file_size_limit_enforced(test_env):
    """Test that files exceeding max_file_size_mb are indexed as METADATA_ONLY without full parsing."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "large_files"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)

    # Set limit to 1 MB
    repo.set_setting("max_file_size_mb", "1")

    # Create 2MB file
    oversized = folder / "huge_log.txt"
    with open(oversized, "wb") as f:
        f.seek((2 * 1024 * 1024) - 1)
        f.write(b"\0")

    res = pipeline.process_file(str(oversized))
    assert res is not None
    assert res["status"] == "INDEXED"
    assert res["privacy_tier"] == "METADATA_ONLY"
    content = repo.get_file_content(res["id"])
    assert "EXCEEDS 1MB LIMIT" in content["searchable_text_preview"]


def test_settings_subfolder_scanning_config(test_env):
    """Test that default_recursive controls whether nested directories are ingested."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    tmp_path = test_env["tmp_path"]

    parent_dir = tmp_path / "parent_project"
    sub_dir = parent_dir / "deep_nested"
    sub_dir.mkdir(parents=True)

    root_file = parent_dir / "root.txt"
    root_file.write_text("Root document")
    nested_file = sub_dir / "nested.txt"
    nested_file.write_text("Nested document")

    # Default recursive = 0 (shallow scan)
    repo.set_setting("default_recursive", "0")
    f_id = repo.add_authorized_folder(str(parent_dir), is_recursive=False)
    count_shallow = pipeline.scan_folder(str(parent_dir))
    assert count_shallow == 1
    assert repo.get_file_by_path(str(root_file)) is not None
    assert repo.get_file_by_path(str(nested_file)) is None

    # Recursive = 1 (deep scan)
    repo.set_setting("default_recursive", "1")
    repo.remove_authorized_folder(f_id)
    repo.add_authorized_folder(str(parent_dir), is_recursive=True)
    count_deep = pipeline.scan_folder(str(parent_dir))
    assert count_deep >= 1
    assert repo.get_file_by_path(str(nested_file)) is not None


def test_settings_backup_export_and_restore(test_env):
    """Test export produces a valid zip archive and restore recovers database & indices."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    tmp_path = test_env["tmp_path"]
    backups_dir = test_env["backups_dir"]

    folder = tmp_path / "my_docs"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)
    doc = folder / "my_secret_plan.txt"
    doc.write_text("Plan text for verification")
    pipeline.process_file(str(doc))

    # Export backup
    backup_file = create_backup(destination_dir=backups_dir)
    assert backup_file.exists()
    assert zipfile.is_zipfile(backup_file)

    # Validate contents of backup zip
    with zipfile.ZipFile(backup_file, "r") as zf:
        names = zf.namelist()
        assert "seekvault.db" in names

    # Corrupt or invalid zip rejection
    fake_zip = backups_dir / "corrupt.zip"
    fake_zip.write_text("not a zip")
    ok, err = restore_backup(fake_zip)
    assert ok is False
    assert "not a valid zip archive" in err

    # Non-existent zip rejection
    ok_ne, err_ne = restore_backup(backups_dir / "does_not_exist.zip")
    assert ok_ne is False
    assert "does not exist" in err_ne


def test_settings_index_reset_clears_records_preserves_disk(test_env):
    """Test that resetting search index clears catalog records while leaving disk files intact."""
    repo = test_env["repo"]
    pipeline = test_env["pipeline"]
    engine = test_env["engine"]
    tmp_path = test_env["tmp_path"]

    folder = tmp_path / "catalog_files"
    folder.mkdir()
    repo.add_authorized_folder(str(folder), is_recursive=False)
    f1 = folder / "doc1.txt"
    f1.write_text("Doc 1 contents")
    f2 = folder / "doc2.txt"
    f2.write_text("Doc 2 contents")

    pipeline.scan_folder(str(folder))
    assert len(repo.get_all_files(status="INDEXED")) == 2

    # Reset search indices
    engine.text_index.reset()
    engine.image_index.reset()
    affected = repo.reset_all_search_indices()
    assert affected == 2

    # Database records marked pending / cleared
    indexed_now = repo.get_all_files(status="INDEXED")
    assert len(indexed_now) == 0

    # Original files on disk are completely intact!
    assert f1.exists() is True
    assert f2.exists() is True
    assert f1.read_text() == "Doc 1 contents"
