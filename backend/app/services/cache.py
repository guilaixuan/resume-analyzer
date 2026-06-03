"""
Redis 缓存包装模块

提供缓存读写操作，当 Redis 不可用时自动降级为内存缓存。
支持：
  - 哈希 key 生成（基于内容）
  - TTL 过期
  - Redis 故障降级
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── 内存缓存（Redis 降级方案） ──
_memory_cache: dict[str, tuple[float, Any]] = {}  # key -> (expire_at, value)


class _RedisClient:
    """惰性初始化的 Redis 客户端包装"""

    def __init__(self):
        self._client: Optional[Any] = None
        self._available: bool = False

    def _connect(self) -> bool:
        if self._available:
            return True
        if not settings.REDIS_HOST:
            self._available = False
            return False
        try:
            import redis as redis_lib
            self._client = redis_lib.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                socket_connect_timeout=2,
                socket_timeout=3,
                decode_responses=True,
            )
            self._client.ping()
            self._available = True
            logger.info("Redis 连接成功: %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
            return True
        except Exception as e:
            self._available = False
            logger.warning("Redis 不可用，使用内存缓存: %s", e)
            return False

    def get(self, key: str) -> Optional[str]:
        if not self._connect():
            return None
        try:
            return self._client.get(key)  # type: ignore
        except Exception as e:
            logger.warning("Redis get 失败: %s", e)
            return None

    def set(self, key: str, value: str, ex: int = 3600) -> bool:
        if not self._connect():
            return False
        try:
            self._client.set(key, value, ex=ex)  # type: ignore
            return True
        except Exception as e:
            logger.warning("Redis set 失败: %s", e)
            return False

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass


_redis = _RedisClient()


def make_cache_key(*parts: str) -> str:
    """
    基于内容生成缓存 key。

    Args:
        *parts: 需要参与哈希的字符串片段

    Returns:
        形如 cache:md5 的 key
    """
    raw = "|".join(parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"cache:{digest}"


def cache_get(key: str) -> Optional[Any]:
    """
    读取缓存。

    Args:
        key: 缓存键

    Returns:
        反序列化后的 Python 对象，未命中返回 None
    """
    # ── Redis 优先 ──
    raw = _redis.get(key)
    if raw is not None:
        try:
            logger.info("缓存命中 (Redis): %s", key)
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # ── 内存缓存 ──
    entry = _memory_cache.get(key)
    if entry:
        expire_at, value = entry
        if time.time() < expire_at:
            logger.info("缓存命中 (Memory): %s", key)
            return value
        else:
            del _memory_cache[key]

    logger.info("缓存未命中: %s", key)
    return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """
    写入缓存。

    Args:
        key: 缓存键
        value: 可 JSON 序列化的 Python 对象
        ttl: 有效期（秒），默认 1 小时
    """
    raw = json.dumps(value, ensure_ascii=False, default=str)

    # ── Redis ──
    _redis.set(key, raw, ex=ttl)

    # ── 内存缓存（双重写入，保证降级时也有效） ──
    _memory_cache[key] = (time.time() + ttl, value)

    logger.info("缓存写入: %s (TTL=%ds)", key, ttl)
