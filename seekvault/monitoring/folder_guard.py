import os
from pathlib import Path
from typing import List, Optional
from seekvault.core.database import get_authorized_folders, add_authorized_folder, remove_authorized_folder
from seekvault.core.logger import logger

class FolderGuard:
    """
    Ensures SeekVault only accesses and indexes user-authorized directories.
    Protects against unauthorized directory access and symlink traversal attacks.
    """
    
    @staticmethod
    def normalize_path(path_str: str) -> str:
        """Resolves symlinks, normalizes Windows paths, and returns absolute path."""
        p = Path(path_str).expanduser()
        resolved = p.resolve()
        return str(resolved)

    @classmethod
    def authorize_folder(cls, folder_path: str, is_recursive: bool = True, db_path: Optional[str] = None) -> str:
        norm_path = cls.normalize_path(folder_path)
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"Folder path '{folder_path}' does not exist.")
        if not os.path.isdir(norm_path):
            raise NotADirectoryError(f"Path '{folder_path}' is not a directory.")
            
        add_authorized_folder(norm_path, is_recursive=is_recursive, custom_db_path=db_path)
        logger.info(f"FolderGuard: Authorized folder path -> {norm_path}")
        return norm_path

    @classmethod
    def revoke_folder(cls, folder_id: int, db_path: Optional[str] = None) -> bool:
        success = remove_authorized_folder(folder_id, custom_db_path=db_path)
        if success:
            logger.info(f"FolderGuard: Revoked folder ID -> {folder_id}")
        return success

    @classmethod
    def get_authorized_paths(cls, db_path: Optional[str] = None) -> List[str]:
        records = get_authorized_folders(active_only=True, custom_db_path=db_path)
        return [r["folder_path"] for r in records]

    @classmethod
    def is_path_authorized(cls, file_or_folder_path: str, db_path: Optional[str] = None) -> bool:
        """
        Verifies if a file or folder path lies inside at least one authorized directory.
        Strict check to prevent access to unauthorized filesystem paths.
        """
        try:
            target = cls.normalize_path(file_or_folder_path)
        except Exception:
            return False
            
        authorized_paths = cls.get_authorized_paths(db_path=db_path)
        for auth_path in authorized_paths:
            try:
                # Check if target is equal to or subpath of auth_path
                target_p = Path(target)
                auth_p = Path(auth_path)
                if target_p == auth_p or auth_p in target_p.parents:
                    return True
            except Exception:
                continue
        return False
