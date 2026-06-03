"""
Pydantic 请求/响应模型定义
"""

from __future__ import annotations

import time
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── 请求模型 ──

class MatchRequest(BaseModel):
    """简历评分请求"""
    resume_json: dict[str, Any] = Field(..., description="AI 提取的简历结构化信息")
    jd_text: str = Field(..., description="岗位需求描述文本")


# ── 响应模型 ──

class ErrorResponse(BaseModel):
    """统一错误响应"""
    error: str
    code: int = 400


class UploadResponse(BaseModel):
    """上传简历的解析结果"""
    text: str = Field(..., description="清洗后的简历纯文本")
    extracted: dict[str, Any] = Field(..., description="AI 提取的结构化信息")
    cached: bool = Field(False, description="是否来自缓存")


class MatchDetail(BaseModel):
    """评分明细项"""
    dimension: str = Field(..., description="评分维度名称")
    weight: float = Field(..., description="权重")
    score: float = Field(..., description="该维度得分 (0-100)")
    detail: str = Field("", description="匹配说明")


class MatchResponse(BaseModel):
    """简历评分响应"""
    score: float = Field(..., description="综合匹配度 0-100", ge=0, le=100)
    details: list[MatchDetail] = Field(..., description="各维度评分明细")
    cached: bool = Field(False, description="是否来自缓存")


class HistoryItem(BaseModel):
    """历史记录条目"""
    timestamp: float = Field(default_factory=time.time)
    jd_preview: str = Field("", description="JD 文本前 100 字")
    score: Optional[float] = None
    resume_name: str = Field("", description="简历文件名")


class HistoryResponse(BaseModel):
    """历史记录响应"""
    records: list[HistoryItem] = Field(default_factory=list)
