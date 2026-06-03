"""
API 路由定义

提供三个核心接口：
  POST /upload  — 上传简历 PDF
  POST /match   — 简历评分匹配
  GET  /history — 历史记录
"""

from __future__ import annotations

import io
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.models.schemas import (
    ErrorResponse,
    HistoryItem,
    HistoryResponse,
    MatchDetail,
    MatchRequest,
    MatchResponse,
    UploadResponse,
)
from app.services.ai_extractor import extract_resume_info
from app.services.cache import cache_get, cache_set, make_cache_key
from app.services.matcher import score_resume
from app.services.pdf_parser import PDFParseError, extract_text
from app.utils.exceptions import (
    AIExtractError,
    FileTooLargeError,
    InvalidFileTypeError,
    PDFParseError as AppPDFParseError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── 内存历史记录 ──
_history: list[dict[str, Any]] = []
MAX_HISTORY = 50


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="上传并解析简历 PDF",
    description="上传 PDF 格式简历文件，返回清洗后的文本和 AI 提取的结构化信息",
)
async def upload_resume(file: UploadFile = File(..., description="PDF 简历文件")):
    """
    上传 PDF 简历并解析：
      1. 校验文件类型和大小
      2. 解析 PDF 提取文本
      3. 调用 AI 提取结构化信息
      4. 返回结果
    """
    # ── 校验文件类型 ──
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise InvalidFileTypeError()

    # ── 读取文件流 ──
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB
        raise FileTooLargeError()

    # ── 检查缓存 ──
    cache_key = make_cache_key("extract", file.filename or "resume", str(len(content)))
    cached = cache_get(cache_key)
    if cached:
        logger.info("简历解析结果命中缓存: %s", file.filename)
        return UploadResponse(**cached, cached=True)

    # ── PDF 解析 ──
    try:
        text = extract_text(io.BytesIO(content))
    except PDFParseError as e:
        raise AppPDFParseError(detail=e.message)
    except Exception as e:
        logger.exception("PDF 解析未知错误")
        raise AppPDFParseError(detail=str(e))

    if not text.strip():
        raise AppPDFParseError(detail="PDF 文件内容为空")

    # ── AI 提取 ──
    try:
        extracted = extract_resume_info(text)
    except Exception as e:
        logger.exception("AI 提取失败")
        raise AIExtractError(detail=str(e))

    # ── 写入缓存 ──
    result_data = {"text": text, "extracted": extracted}
    cache_set(cache_key, result_data, ttl=3600)

    # ── 记录历史 ──
    _add_history({
        "timestamp": time.time(),
        "jd_preview": "",
        "score": None,
        "resume_name": file.filename or "unknown.pdf",
    })

    return UploadResponse(text=text, extracted=extracted, cached=False)


@router.post(
    "/match",
    response_model=MatchResponse,
    responses={400: {"model": ErrorResponse}},
    summary="简历评分与岗位匹配",
    description="传入简历提取结果和 JD 文本，返回匹配度评分",
)
async def match_resume(req: MatchRequest):
    """
    评估简历与岗位匹配度：
      1. 校验输入
      2. 检查缓存
      3. AI 分析 JD + 加权规则评分
      4. 缓存结果
    """
    if not req.jd_text.strip():
        raise HTTPException(status_code=400, detail="岗位描述不能为空")

    if not req.resume_json:
        raise HTTPException(status_code=400, detail="简历信息不能为空")

    # ── 检查缓存 ──
    cache_key = make_cache_key(
        "match",
        str(req.resume_json.get("name", "")),
        req.jd_text[:200],
    )
    cached = cache_get(cache_key)
    if cached:
        logger.info("评分结果命中缓存")
        return MatchResponse(**cached, cached=True)

    # ── 评分 ──
    try:
        result = score_resume(req.resume_json, req.jd_text)
    except Exception as e:
        logger.exception("评分失败")
        raise HTTPException(status_code=500, detail=f"评分失败: {e}")

    # ── 写入缓存 ──
    cache_set(cache_key, result, ttl=3600)

    # ── 记录历史 ──
    _add_history({
        "timestamp": time.time(),
        "jd_preview": req.jd_text[:100],
        "score": result["score"],
        "resume_name": req.resume_json.get("name", "unknown"),
    })

    return MatchResponse(
        score=result["score"],
        details=[MatchDetail(**d) for d in result["details"]],
        cached=False,
    )


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="查询历史记录",
    description="返回最近的简历解析和评分历史记录",
)
async def get_history():
    """返回历史记录列表"""
    return HistoryResponse(
        records=[HistoryItem(**item) for item in _history]
    )


def _add_history(item: dict[str, Any]) -> None:
    """添加一条历史记录，超出上限时移除最旧的"""
    _history.insert(0, item)
    while len(_history) > MAX_HISTORY:
        _history.pop()
