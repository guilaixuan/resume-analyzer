"""
阿里云函数计算 FC 入口

FC Python 运行时需要暴露一个 `handler` 函数作为入口。
使用 Web 框架模式（Custom Runtime）托管 FastAPI 应用。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.main import app

logger = logging.getLogger(__name__)


def handler(event: bytes, context: Any) -> bytes:
    """
    FC 事件/HTTP 入口函数。

    Args:
        event: 请求事件 bytes
        context: FC 运行时上下文

    Returns:
        响应 bytes (JSON)
    """
    logger.info("FC handler invoked")

    # 对于 HTTP 触发器，FastAPI 直接通过 uvicorn 运行
    # 此 handler 作为 Custom Runtime 的备用入口
    return json.dumps({"status": "ok", "message": "Resume Analyzer API is running"}).encode("utf-8")
