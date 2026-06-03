"""
PDF 简历解析模块

双引擎设计：
  主引擎 pdfplumber — 文本提取质量高
  备用引擎 PyMuPDF  — 处理扫描件/复杂版式时兜底
"""

from __future__ import annotations

import io
import logging
import re
from typing import Optional

import pdfplumber
from pdfplumber.pdf import PDF as PDFPlumberPDF

logger = logging.getLogger(__name__)


class PDFParseError(Exception):
    """PDF 解析异常"""
    def __init__(self, message: str, code: int = 4002):
        self.message = message
        self.code = code
        super().__init__(self.message)


def extract_text(file_stream: io.BytesIO) -> str:
    """
    从 PDF 文件流中提取并清洗纯文本。

    Args:
        file_stream: 上传的 PDF 文件二进制流

    Returns:
        清洗后的纯文本字符串

    Raises:
        PDFParseError: 解析失败时抛出
    """
    raw_text = ""
    errors: list[str] = []

    # ── 主引擎：pdfplumber ──
    try:
        file_stream.seek(0)
        pdf: PDFPlumberPDF = pdfplumber.open(file_stream)
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        pdf.close()
        raw_text = "\n".join(pages_text)
    except Exception as e:
        errors.append(f"pdfplumber: {e}")
        logger.warning("pdfplumber 解析失败，尝试 PyMuPDF: %s", e)

    # ── 主引擎为空时，用备用引擎 PyMuPDF ──
    if not raw_text.strip():
        try:
            import fitz  # PyMuPDF

            file_stream.seek(0)
            pdf_doc = fitz.open(stream=file_stream.read(), filetype="pdf")
            pages_text = []
            for page_num in range(len(pdf_doc)):
                text = pdf_doc[page_num].get_text()
                if text:
                    pages_text.append(text)
            pdf_doc.close()
            raw_text = "\n".join(pages_text)
            if raw_text.strip():
                logger.info("PyMuPDF 备用引擎成功提取文本")
        except Exception as e:
            errors.append(f"PyMuPDF: {e}")
            logger.error("PyMuPDF 也解析失败: %s", e)

    # ── 两个引擎都失败 ──
    if not raw_text.strip():
        error_msg = f"PDF 解析失败: {'; '.join(errors)}" if errors else "PDF 文件为空或无法解析"
        raise PDFParseError(error_msg)

    # ── 文本清洗 ──
    cleaned = _clean_text(raw_text)
    logger.info("PDF 解析成功，提取 %d 字符 (清洗后 %d 字符)", len(raw_text), len(cleaned))
    return cleaned


def _clean_text(text: str) -> str:
    """
    清洗 PDF 提取的原始文本：
      - 移除多余空白和空行
      - 合并断裂的单词（连字符断词）
      - 去除控制字符
      - 规范化换行
    """
    # 去除控制字符（保留换行和制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 合并连字符断词（如 "resu-\nme" → "resume"）
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # 将多个空行压缩为单个空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 去除每行首尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # 去除多余空白（保留段落间空行）
    text = re.sub(r'[ \t]+', ' ', text)

    # 移除只有标点的空行
    text = re.sub(r'\n[.,;:!?\-—·•]+\n', '\n', text)

    return text.strip()
