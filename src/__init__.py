from loguru import logger

from src.config import logger_config

logger.configure(**logger_config)
