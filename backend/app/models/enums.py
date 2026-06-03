"""
枚举与常量定义
"""

from enum import Enum


class ErrorCode(int, Enum):
    """业务错误码"""
    SUCCESS = 0
    INVALID_FILE = 4001       # 文件格式/大小不符
    PDF_PARSE_FAILED = 4002   # PDF 解析失败
    AI_EXTRACT_FAILED = 4003  # AI 提取失败
    SCORE_FAILED = 4004       # 评分失败
    INVALID_JD = 4005         # JD 文本为空
    INTERNAL_ERROR = 5000     # 内部错误
