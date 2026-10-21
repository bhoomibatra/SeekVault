import os
import sys
import subprocess
from pathlib import Path

def main():
    print("==================================================")
    print("🛡️  SEEKVAULT PROTOTYPE: DEMONSTRATION LAUNCHER")
    print("==================================================")

    base_dir = Path(__file__).resolve().parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    sample_script = base_dir / "sample_data" / "create_samples.py"

    # 1. Generate sample data if needed
    print("\n[Step 1/3] Checking demo sample datasets...")
    subprocess.run([sys.executable, str(sample_script)], check=True)

    # 2. Pre-seed authorized folders & run initial indexing
    print("\n[Step 2/3] Seeding database with authorized folders & indexing files...")
    from seekvault.database.repository import Repository
    from seekvault.search.engine import SearchEngine
    from seekvault.ingestion.pipeline import IngestionPipeline

    repo = Repository()
    search_engine = SearchEngine(repository=repo)
    pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

    sample_folders = [
        base_dir / "sample_data" / "authorized_academic",
        base_dir / "sample_data" / "authorized_personal",
        base_dir / "sample_data" / "authorized_images",
        base_dir / "sample_data" / "authorized_versions",
    ]

    total_ingested = 0
    for folder in sample_folders:
        if folder.exists():
            repo.add_authorized_folder(str(folder), is_recursive=True)
            count = pipeline.scan_folder(str(folder), is_recursive=True)
            print(f"  ✓ Ingested folder: {folder.name} ({count} files)")
            total_ingested += count

    print(f"\nIndexed total of {total_ingested} files across authorized folders.")

    # 3. Launch Streamlit Application
    print("\n[Step 3/3] Starting Streamlit interface on http://localhost:8501 ...")
    app_path = base_dir / "app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.headless", "true"
    ])

if __name__ == "__main__":
    main()
