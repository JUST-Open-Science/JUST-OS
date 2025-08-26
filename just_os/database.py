import logging
from typing import Optional
from redis import Redis

from config.settings import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """
    Get or create a Redis client instance.
    Uses a singleton pattern to avoid creating multiple connections.

    Returns:
        Redis: The Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = Redis(
                host=DEFAULT_CONFIG["REDIS_HOST"],
                port=DEFAULT_CONFIG["REDIS_PORT"],
                db=DEFAULT_CONFIG["REDIS_DB"],
            )
            logger.debug("Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise

    return _redis_client
