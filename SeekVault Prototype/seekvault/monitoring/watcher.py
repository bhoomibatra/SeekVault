import os
import threading
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from seekvault.database.repository import Repository
from seekvault.monitoring.handler import FolderEventHandler
import logging

logger = logging.getLogger(__name__)

class WatcherManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.repository = pipeline.repository
        self.observer = Observer()
        self.handler = FolderEventHandler(self.pipeline)
        self.watches: Dict[str, Any] = {}
        self.is_running = False

    @classmethod
    def get_instance(cls, pipeline) -> "WatcherManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(pipeline)
            return cls._instance

    def start(self) -> None:
        if not self.is_running:
            self.observer.start()
            self.is_running = True
            self.sync_watches()
            logger.info("SeekVault Watchdog Observer started.")

    def stop(self) -> None:
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("SeekVault Watchdog Observer stopped.")

    def sync_watches(self) -> None:
        """Synchronize active watches with the currently authorized folders in SQLite."""
        if not self.is_running:
            return

        active_folders = self.repository.get_authorized_folders(active_only=True)
        active_paths = {f["folder_path"]: bool(f["is_recursive"]) for f in active_folders}

        # Remove watches no longer authorized
        for path in list(self.watches.keys()):
            if path not in active_paths:
                try:
                    self.observer.unschedule(self.watches[path])
                    del self.watches[path]
                    logger.info(f"Unscheduled watchdog for folder: {path}")
                except Exception as e:
                    logger.error(f"Error unscheduling watch for {path}: {e}")

        # Add new authorized watches
        for path, recursive in active_paths.items():
            if path not in self.watches and os.path.exists(path):
                try:
                    watch = self.observer.schedule(self.handler, path=path, recursive=recursive)
                    self.watches[path] = watch
                    logger.info(f"Scheduled watchdog on: {path} (recursive={recursive})")
                except Exception as e:
                    logger.error(f"Error scheduling watch for {path}: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "watched_folder_count": len(self.watches),
            "watched_paths": list(self.watches.keys())
        }
