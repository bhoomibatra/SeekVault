"""
test_live_drop_search.py — Test live file ingestion and discovery without restarting the app.

Verifies:
1. A new file dropped into an active authorized directory is ingested.
2. The shared SearchEngine instance immediately discovers the new file via search.
3. No app restart, database re-initialization, or service restart is required.
"""

import tempfile
from pathlib import Path
import pytest

from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.handler import FolderEventHandler


def test_live_file_drop_becomes_searchable_without_restart():
    """Verify that dropping a file into an authorized folder immediately makes it searchable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_path = root / "live_test.db"
        with get_db_connection(db_path) as conn:
            init_db(conn)

        repo = Repository(db_path=db_path)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=root / "live_text.faiss",
            text_meta_path=root / "live_text.json",
            image_index_path=root / "live_image.faiss",
            image_meta_path=root / "live_image.json",
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)
        handler = FolderEventHandler(pipeline)

        # 1. Authorize test directory
        watch_dir = root / "monitored_vault"
        watch_dir.mkdir()
        repo.add_authorized_folder(str(watch_dir), is_recursive=True)

        # 2. Pre-condition: Search for query before file exists returns 0 results
        pre_results = search_engine.search_text("astrophysics gravitational lensing redshift", top_k=5)
        assert len(pre_results) == 0

        # 3. Simulate dropping a new file live into the authorized folder
        new_doc = watch_dir / "Gravitational_Waves_Research.txt"
        new_doc.write_text(
            "Gravitational lensing and cosmic redshift observations in astrophysics deep field studies.",
            encoding="utf-8"
        )

        # 4. Trigger watchdog event handler on file creation
        from watchdog.events import FileCreatedEvent
        handler.on_created(FileCreatedEvent(str(new_doc)))

        # 5. Invariant: SearchEngine immediately returns the newly dropped file without any restart
        post_results = search_engine.search_text("astrophysics gravitational lensing redshift", top_k=5)
        assert len(post_results) > 0, "Newly dropped file was not immediately discoverable via search!"
        assert post_results[0]["file_name"] == "Gravitational_Waves_Research.txt"
        assert post_results[0]["similarity_score"] > 0.3
