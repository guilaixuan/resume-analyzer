"""
AI 简历信息提取 & JD 关键词分析模块

使用 OpenAI 兼容接口（兼容 DeepSeek / 通义千问 / 智谱等），
从简历文本中提取结构化信息，从岗位 JD 中提取关键词。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import openai

from app.config import settings

logger = logging.getLogger(__name__)

# ── 客户端（懒加载） ──

_client: Optional[openai.OpenAI] = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        kwargs = dict(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )
        if settings.HTTP_PROXY:
            try:
                from openai import DefaultHttpxClient
                kwargs["http_client"] = DefaultHttpxClient(proxy=settings.HTTP_PROXY)
            except ImportError:
                pass
        _client = openai.OpenAI(**kwargs)
    return _client


# ── Prompt 模板 ──

EXTRACT_PROMPT = """你是一个专业的简历解析助手。请从以下简历文本中提取关键信息，以 JSON 格式返回。

必须提取的字段（尽力而为，找不到则填 null）：
- name: 姓名
- phone: 电话号码
- email: 邮箱地址
- address: 地址（城市/地区）

可选提取的字段（找到就填，找不到就省略）：
- job_intention: 求职意向/期望岗位
- expected_salary: 期望薪资
- work_years: 工作年限（数字，如 3）
- education: 最高学历（如 本科/硕士/博士）
- schools: 毕业院校列表（数组）
- majors: 专业列表（数组）
- skills: 掌握的技能列表（数组）
- project_experience: 项目经历简述（最多 200 字）

请严格输出一个 JSON 对象，不要包含 markdown 代码块标记或其他说明文字。

简历文本：
---
{text}
---"""

JD_ANALYSIS_PROMPT = """你是一个岗位需求分析专家。请分析以下职位描述（JD），提取关键招聘要求，以 JSON 格式返回。

字段说明：
- required_skills: 必备技能列表（数组）
- preferred_skills: 加分技能列表（数组）
- education_requirement: 学历要求（如 本科/硕士/不限）
- experience_requirement: 经验要求描述
- keywords: 所有重要的关键词列表（用于简历匹配）

请严格输出一个 JSON 对象，不要包含 markdown 代码块标记或其他说明文字。

JD 文本：
---
{jd_text}
---"""


# ── 核心函数 ──

def _call_ai(prompt: str, max_retries: int = 2) -> str:
    """
    调用 AI 模型并返回原始文本响应。

    Args:
        prompt: 发送给模型的 prompt
        max_retries: 最大重试次数

    Returns:
        模型返回的原始文本

    Raises:
        RuntimeError: 所有重试都失败时抛出
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = _get_client().chat.completions.create(
                model=settings.AI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
                timeout=60,
            )
            content = resp.choices[0].message.content or ""
            logger.info(
                "AI 调用成功 (attempt=%d, input=%d chars, output=%d chars)",
                attempt + 1, len(prompt), len(content),
            )
            return content
        except Exception as e:
            last_error = e
            logger.warning("AI 调用失败 (attempt=%d): %s", attempt + 1, e)

    raise RuntimeError(f"AI 调用全部失败: {last_error}")


def _parse_json_response(text: str) -> dict[str, Any]:
    """
    从 AI 响应文本中解析 JSON，兼容各种格式问题。
    """
    # 尝试去除可能的 markdown 代码块标记
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试从文本中提取第一个 {…} 块
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise


def extract_resume_info(resume_text: str) -> dict[str, Any]:
    """
    从简历文本中提取结构化信息。

    Args:
        resume_text: 清洗后的简历纯文本

    Returns:
        结构化字典，包含姓名/电话/邮箱等字段
        当 AI 完全失败时，返回仅包含 text 字段的降级结果
    """
    prompt = EXTRACT_PROMPT.format(text=resume_text[:8000])  # 截断防止超出 token 限制

    try:
        raw = _call_ai(prompt)
        result = _parse_json_response(raw)
        logger.info("简历信息提取成功: %s", result.get("name", "unknown"))
        return result
    except Exception as e:
        logger.error("简历信息提取失败，使用降级方案: %s", e)
        return _fallback_extract(resume_text)


def _fallback_extract(text: str) -> dict[str, Any]:
    """
    降级方案：使用正则粗略提取基本信息
    """
    result: dict[str, Any] = {"_fallback": True}

    # 姓名：假设简历第一行是姓名（简单处理）
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        first_line = lines[0]
        if len(first_line) <= 10 and not re.search(r'[^一-鿿\sa-zA-Z]', first_line):
            result["name"] = first_line

    # 电话：匹配中国大陆手机号
    phone_match = re.search(r'(1[3-9]\d{9})', text)
    if phone_match:
        result["phone"] = phone_match.group(1)

    # 邮箱
    email_match = re.search(r'[\w.+-]+@[\w-]+\.\w+', text)
    if email_match:
        result["email"] = email_match.group(0)

    # 地址：匹配常见城市
    cities = re.findall(r'(北京|上海|广州|深圳|杭州|成都|武汉|南京|天津|重庆|苏州|西安|长沙)', text)
    if cities:
        result["address"] = cities[0]

    # 工作年限
    year_match = re.search(r'(\d+)\s*年', text)
    if year_match:
        result["work_years"] = int(year_match.group(1))

    # 学历
    edu_match = re.search(r'(博士|硕士|本科|大专)', text)
    if edu_match:
        result["education"] = edu_match.group(1)

    logger.info("降级提取完成: %s", result)
    return result


def analyze_jd(jd_text: str) -> dict[str, Any]:
    """
    分析岗位 JD，提取关键词和要求。

    Args:
        jd_text: 岗位需求描述文本

    Returns:
        包含 skills/education/keywords 等字段的字典
    """
    prompt = JD_ANALYSIS_PROMPT.format(jd_text=jd_text[:4000])

    try:
        raw = _call_ai(prompt)
        result = _parse_json_response(raw)
        logger.info("JD 分析成功，提取 %d 个技能关键词", len(result.get("keywords", [])))
        return result
    except Exception as e:
        logger.error("JD 分析失败，使用降级方案: %s", e)
        return _fallback_analyze_jd(jd_text)


def _fallback_analyze_jd(jd_text: str) -> dict[str, Any]:
    """
    降级：通过规则粗略提取 JD 关键词
    """
    # 常见技能关键词
    SKILL_KEYWORDS = [
        "Python", "Java", "Go", "JavaScript", "TypeScript", "C++", "React",
        "Vue", "Angular", "Docker", "Kubernetes", "Redis", "MySQL", "PostgreSQL",
        "MongoDB", "FastAPI", "Flask", "Django", "Spring", "TensorFlow",
        "PyTorch", "AWS", "阿里云", "Linux", "Git", "REST", "GraphQL",
        "Machine Learning", "Deep Learning", "NLP", "数据分析", "后端开发",
    ]

    found_skills = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in jd_text.lower():
            found_skills.append(skill)

    edu = "不限"
    for e in ["博士", "硕士", "本科", "大专"]:
        if e in jd_text:
            edu = e
            break

    return {
        "required_skills": found_skills,
        "preferred_skills": [],
        "education_requirement": edu,
        "experience_requirement": "",
        "keywords": found_skills,
    }
