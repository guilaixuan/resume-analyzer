"""
全局异常处理

定义业务异常类和 FastAPI 异常处理器。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.enums import ErrorCode

logger = logging.getLogger(__name__)


class AppException(Exception):
    """业务异常基类"""

    def __init__(self, message: str, code: int = 4000, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class FileTooLargeError(AppException):
    """文件过大异常"""
    def __init__(self, max_size_mb: int = 10):
        super().__init__(
            message=f"文件大小超过 {max_size_mb}MB 限制",
            code=ErrorCode.INVALID_FILE,
        )


class InvalidFileTypeError(AppException):
    """文件类型异常"""
    def __init__(self):
        super().__init__(
            message="仅支持 PDF 格式文件",
            code=ErrorCode.INVALID_FILE,
        )


class PDFParseError(AppException):
    """PDF 解析异常"""
    def __init__(self, detail: str = "PDF 解析失败"):
        super().__init__(
            message=detail,
            code=ErrorCode.PDF_PARSE_FAILED,
        )


class AIExtractError(AppException):
    """AI 提取异常"""
    def __init__(self, detail: str = "AI 信息提取失败"):
        super().__init__(
            message=detail,
            code=ErrorCode.AI_EXTRACT_FAILED,
        )


# ── FastAPI 异常处理器 ──

def register_exception_handlers(app: "FastAPI") -> None:
    """
    在 FastAPI 应用上注册全局异常处理器。

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """业务异常处理"""
        logger.warning("业务异常: [%d] %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """参数校验异常处理"""
        errors = exc.errors()
        detail = "; ".join(
            f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg', '')}"
            for e in errors
        )
        logger.warning("参数校验失败: %s", detail)
        return JSONResponse(
            status_code=422,
            content={"error": f"参数校验失败: {detail}", "code": 422},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """全局兜底异常处理"""
        logger.exception("未捕获异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "服务器内部错误，请稍后重试",
                "code": ErrorCode.INTERNAL_ERROR,
            },
        )
