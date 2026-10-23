"""
test_duplicates_versions_ui.py — Tests for TASK-15 version dismissal, suggestions, and duplicate calculation.
"""

from pathlib import Path
import pytest

from seekvault.database.repository import Repository
from seekvault.ui.pages.duplicates_versions import render_duplicates_versions_page


def test_duplicates_versions_callable():
    """Verify render function is callable."""
    assert callable(render_duplicates_versions_page)


def test_version_dismissal_and_restoration(tmp_path):
    """
    R-23 & N-7 & TASK-15:
    Users must be able to dismiss incorrect version suggestions and restore them.
    Dismissed items must be filtered out from active version group views.
    """
    db_file = tmp_path / "test_ver_dismiss.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "reports"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "Report_Draft_v1.docx"
    f1.write_text("Draft version 1", encoding="utf-8")
    rid1 = repo.upsert_file(folder_id=fid, file_path=str(f1), file_name="Report_Draft_v1.docx", file_extension=".docx", file_size=100, file_hash="h1", file_type="DOCUMENT", modified_at="2026-01-01", status="INDEXED")

    f2 = folder / "Report_Draft_v2.docx"
    f2.write_text("Draft version 2", encoding="utf-8")
    rid2 = repo.upsert_file(folder_id=fid, file_path=str(f2), file_name="Report_Draft_v2.docx", file_extension=".docx", file_size=110, file_hash="h2", file_type="DOCUMENT", modified_at="2026-01-02", status="INDEXED")

    # Create version group with both files
    vg_id = repo.save_version_group("Report_draft", [(rid1, 1.0, 1), (rid2, 0.88, 2)])

    # Initially, both members active
    vgs = repo.get_all_version_groups(include_dismissed=False)
    assert len(vgs) == 1
    assert len(vgs[0]["members"]) == 2

    # Dismiss member 2
    mem2_id = vgs[0]["members"][1]["id"]
    dismissed = repo.dismiss_version_member(mem2_id)
    assert dismissed

    # Check active view excludes dismissed member
    vgs_active = repo.get_all_version_groups(include_dismissed=False)
    assert len(vgs_active[0]["members"]) == 1
    assert vgs_active[0]["members"][0]["id"] != mem2_id

    # Check full view includes dismissed member marked with is_dismissed = 1
    vgs_all = repo.get_all_version_groups(include_dismissed=True)
    assert len(vgs_all[0]["members"]) == 2
    dismissed_rec = next(m for m in vgs_all[0]["members"] if m["id"] == mem2_id)
    assert dismissed_rec["is_dismissed"] == 1

    # Restore member
    restored = repo.restore_version_member(mem2_id)
    assert restored
    vgs_restored = repo.get_all_version_groups(include_dismissed=False)
    assert len(vgs_restored[0]["members"]) == 2


def test_duplicate_reclaimable_space_calculation(tmp_path):
    """
    R-22 & TASK-15:
    Exact duplicate groups calculate potential reclaimable space correctly.
    """
    db_file = tmp_path / "test_dup_calc.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "data"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    # Create 3 identical files (1000 bytes each) sharing the same hash
    for i in range(1, 4):
        f = folder / f"copy_{i}.pdf"
        f.write_bytes(b"X" * 1000)
        repo.upsert_file(
            folder_id=fid,
            file_path=str(f),
            file_name=f"copy_{i}.pdf",
            file_extension=".pdf",
            file_size=1000,
            file_hash="identical_hash_abc",
            file_type="DOCUMENT",
            modified_at="2026-01-01",
            status="INDEXED"
        )

    dup_groups = repo.get_duplicate_groups()
    assert len(dup_groups) == 1
    group = dup_groups[0]
    assert group["file_count"] == 3
    assert group["total_size"] == 3000
    # 3 copies of 1000 bytes -> 2 copies redundant -> 2000 bytes reclaimable
    assert group["reclaimable_size"] == 2000
