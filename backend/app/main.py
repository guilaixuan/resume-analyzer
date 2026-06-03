"""
星使智算 - 智能简历分析系统 API

FastAPI 应用入口，包含 CORS 配置、异常处理和路由注册。
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.router import router
from app.utils.exceptions import register_exception_handlers
from app.utils.logger import setup_logger

# ── 日志初始化 ──
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("📄 智能简历分析系统启动")
    logger.info("AI 模型: %s | 缓存: Redis + Memory | CORS: %s", settings.AI_MODEL, settings.CORS_ORIGINS)
    yield
    logger.info("🛑 智能简历分析系统关闭")


app = FastAPI(
    title="智能简历分析系统",
    description="AI 赋能的简历解析、信息提取与岗位匹配度评分 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS 配置（允许 GitHub Pages 调用） ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册异常处理器 ──
register_exception_handlers(app)

# ── 注册路由 ──
app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
