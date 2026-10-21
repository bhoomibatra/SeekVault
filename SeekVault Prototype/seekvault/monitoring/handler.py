import time
import os
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from seekvault.config import ALL_SUPPORTED_EXTENSIONS, WATCHDOG_DEBOUNCE_SECONDS
import logging

logger = logging.getLogger(__name__)

class FolderEventHandler(FileSystemEventHandler):
    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self._last_processed = {}

    def _should_debounce(self, path: str) -> bool:
        now = time.time()
        last_time = self._last_processed.get(path, 0)
        if now - last_time < WATCHDOG_DEBOUNCE_SECONDS:
            return True
        self._last_processed[path] = now
        return False

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext in ALL_SUPPORTED_EXTENSIONS:
            if not self._should_debounce(path):
                logger.info(f"Watchdog: New file detected: {path}")
                try:
                    time.sleep(0.5)  # Let file write complete
                    self.pipeline.process_file(path)
                except Exception as e:
                    logger.error(f"Error processing new file {path}: {e}")

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext in ALL_SUPPORTED_EXTENSIONS:
            if not self._should_debounce(path):
                logger.info(f"Watchdog: File modified: {path}")
                try:
                    time.sleep(0.5)
                    self.pipeline.process_file(path)
                except Exception as e:
                    logger.error(f"Error reprocessing modified file {path}: {e}")

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext in ALL_SUPPORTED_EXTENSIONS:
            logger.info(f"Watchdog: File deleted: {path}")
            try:
                self.pipeline.remove_file(path)
            except Exception as e:
                logger.error(f"Error removing deleted file {path}: {e}")

    def on_moved(self, event):
        if event.is_directory:
            return
        src_path = event.src_path
        dest_path = event.dest_path
        logger.info(f"Watchdog: File moved from {src_path} to {dest_path}")
        try:
            self.pipeline.remove_file(src_path)
            ext = os.path.splitext(dest_path)[1].lower()
            if ext in ALL_SUPPORTED_EXTENSIONS:
                self.pipeline.process_file(dest_path)
        except Exception as e:
            logger.error(f"Error handling moved file: {e}")
