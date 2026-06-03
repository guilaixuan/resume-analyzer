"""
应用配置管理 - 从环境变量读取，提供合理的默认值
"""

import os
from typing import Optional


class Settings:
    # ── AI API ──
    AI_API_KEY: str = os.getenv("AI_API_KEY", "sk-403e3fd6ca9944dc82f61e94f8e044bf")
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-chat")

    # ── Redis ──
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD") or None
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # ── 阿里云 FC ──
    FC_REGION: str = os.getenv("FC_REGION", "cn-hangzhou")
    FC_SERVICE_NAME: str = os.getenv("FC_SERVICE_NAME", "resume-analyzer")
    FC_FUNCTION_NAME: str = os.getenv("FC_FUNCTION_NAME", "resume-api")

    # ── 服务 ──
    CACHE_TTL: int = 3600  # 缓存有效期 1 小时
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 最大上传 10 MB
    HISTORY_MAX: int = 50  # 历史记录最多保留条数

    # ── CORS ──
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "https://your-username.github.io,http://localhost:5500",
    ).split(",")


settings = Settings()
