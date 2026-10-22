import logging
import sys
from seekvault.config import LOG_PATH

def get_logger(name: str = "seekvault") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console Handler
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)
        
        # File Handler
        f_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        f_handler.setFormatter(formatter)
        logger.addHandler(f_handler)
        
    return logger

logger = get_logger()
