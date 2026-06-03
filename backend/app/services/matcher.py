"""
简历评分与岗位匹配模块

采用 AI + 加权规则 双引擎评分策略：
  1. 用 AI 从 JD 中提取关键词和硬性要求
  2. 基于预定义的加权规则计算各维度分数
  3. 综合得出 0-100 的匹配度评分
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.ai_extractor import analyze_jd

logger = logging.getLogger(__name__)


# ── 加权评分规则 ──

SCORE_RULES: list[dict[str, Any]] = [
    {"dimension": "技能匹配", "weight": 0.50, "description": "必备技能与简历技能的覆盖率"},
    {"dimension": "学历匹配", "weight": 0.20, "description": "学历要求是否满足"},
    {"dimension": "经验匹配", "weight": 0.20, "description": "工作年限与经验要求匹配度"},
    {"dimension": "意向匹配", "weight": 0.10, "description": "求职意向与岗位契合度"},
]

# 学历层级映射（用于学历匹配度计算）
EDUCATION_LEVELS: dict[str, int] = {
    "不限": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4,
}


def score_resume(resume_info: dict[str, Any], jd_text: str) -> dict[str, Any]:
    """
    综合评估简历与岗位 JD 的匹配度。

    Args:
        resume_info: ai_extractor 提取的简历结构化信息
        jd_text: 岗位需求描述文本

    Returns:
        {
            "score": 0-100 综合评分,
            "details": [{ "dimension", "weight", "score", "detail" }, ...]
        }
    """
    # Step 1: AI 分析 JD 提取关键词
    jd_analysis = analyze_jd(jd_text)

    # Step 2: 计算各维度分数
    details = []

    # ── 技能匹配 ──
    skill_detail = _calc_skill_match(resume_info, jd_analysis)
    details.append(skill_detail)

    # ── 学历匹配 ──
    edu_detail = _calc_education_match(resume_info, jd_analysis)
    details.append(edu_detail)

    # ── 经验匹配 ──
    exp_detail = _calc_experience_match(resume_info, jd_analysis)
    details.append(exp_detail)

    # ── 意向匹配 ──
    intention_detail = _calc_intention_match(resume_info, jd_analysis)
    details.append(intention_detail)

    # Step 3: 加权综合
    total_score = 0.0
    for d in details:
        total_score += d["score"] * d["weight"]

    total_score = round(min(max(total_score, 0), 100), 1)

    logger.info(
        "简历评分完成: %.1f 分 (技能=%.1f, 学历=%.1f, 经验=%.1f, 意向=%.1f)",
        total_score,
        details[0]["score"], details[1]["score"],
        details[2]["score"], details[3]["score"],
    )

    return {
        "score": total_score,
        "details": details,
    }


def _calc_skill_match(resume: dict[str, Any], jd: dict[str, Any]) -> dict[str, Any]:
    """
    计算技能匹配度。
    比较 JD 要求的必备技能与简历中出现的技能。
    """
    required = jd.get("required_skills", [])
    preferred = jd.get("preferred_skills", [])
    all_required = required + preferred

    # 从简历中收集所有技能相关信息
    resume_skills = set()
    for key in ["skills", "keywords", "project_experience"]:
        val = resume.get(key, [])
        if isinstance(val, list):
            for item in val:
                resume_skills.add(str(item).lower())
        elif isinstance(val, str):
            resume_skills.add(val.lower())

    # 求职意向和项目经历中也包含技能信息
    job_int = (resume.get("job_intention") or "").lower()
    proj_exp = (resume.get("project_experience") or "").lower()

    if not all_required:
        # 没有明确的技能要求，默认 70 分
        return {
            "dimension": "技能匹配",
            "weight": 0.50,
            "score": 70.0,
            "detail": "JD 中未明确要求技能，默认中等偏上评分",
        }

    matched = 0
    matched_skills = []
    missing_skills = []

    for skill in all_required:
        skill_lower = skill.lower()
        if skill_lower in resume_skills or skill_lower in job_int or skill_lower in proj_exp:
            matched += 1
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    match_rate = matched / len(all_required) if all_required else 0
    score = round(match_rate * 100, 1)

    detail = (
        f"已匹配技能: {', '.join(matched_skills[:5])}" if matched_skills else "未匹配到技能"
    )
    if missing_skills:
        detail += f" | 缺失: {', '.join(missing_skills[:3])}"

    return {
        "dimension": "技能匹配",
        "weight": 0.50,
        "score": min(score, 100),
        "detail": detail,
    }


def _calc_education_match(resume: dict[str, Any], jd: dict[str, Any]) -> dict[str, Any]:
    """
    计算学历匹配度。
    """
    edu_require = jd.get("education_requirement", "不限")
    resume_edu = resume.get("education", "")

    require_level = EDUCATION_LEVELS.get(edu_require, 0)
    resume_level = EDUCATION_LEVELS.get(resume_edu, 0)

    if require_level == 0:
        # 无学历要求，满分
        return {
            "dimension": "学历匹配",
            "weight": 0.20,
            "score": 100.0,
            "detail": f"岗位无学历要求，简历学历: {resume_edu or '未填写'}",
        }

    if resume_level == 0 and resume_edu:
        # 有学历信息但无法映射到层级
        return {
            "dimension": "学历匹配",
            "weight": 0.20,
            "score": 50.0,
            "detail": f"岗位要求: {edu_require}，简历学历无法确定层级: {resume_edu}",
        }

    if resume_level >= require_level:
        return {
            "dimension": "学历匹配",
            "weight": 0.20,
            "score": 100.0,
            "detail": f"岗位要求: {edu_require}，简历学历: {resume_edu} — 满足要求",
        }

    score = max(resume_level / require_level * 60, 20)
    return {
        "dimension": "学历匹配",
        "weight": 0.20,
        "score": round(score, 1),
        "detail": f"岗位要求: {edu_require}，简历学历: {resume_edu} — 略低于要求",
    }


def _calc_experience_match(resume: dict[str, Any], jd: dict[str, Any]) -> dict[str, Any]:
    """
    计算经验匹配度。
    """
    resume_years = resume.get("work_years")
    exp_require = jd.get("experience_requirement", "")

    if resume_years is None:
        return {
            "dimension": "经验匹配",
            "weight": 0.20,
            "score": 50.0,
            "detail": "简历未提供明确工作年限，默认中等评分",
        }

    # 从 JD 描述中提取年限要求
    year_matches = re.findall(r'(\d+)\s*[年以\-到至]+\s*(\d*)\s*年', exp_require)
    if not year_matches:
        year_matches = re.findall(r'(\d+)\s*年', exp_require)

    if not year_matches:
        # JD 未明确要求年限
        return {
            "dimension": "经验匹配",
            "weight": 0.20,
            "score": 80.0,
            "detail": f"JD 未明确经验要求，简历年限: {resume_years} 年",
        }

    # 简单判断：如果 JD 要求 N 年以上，简历年限 >= N 则满分
    required_years = int(year_matches[0][0]) if isinstance(year_matches[0], tuple) else int(year_matches[0])
    if resume_years >= required_years:
        score = 100.0
    elif resume_years >= required_years * 0.7:
        score = 70.0
    elif resume_years >= required_years * 0.4:
        score = 40.0
    else:
        score = 20.0

    return {
        "dimension": "经验匹配",
        "weight": 0.20,
        "score": round(score, 1),
        "detail": f"岗位要求: {required_years}+ 年，简历: {resume_years} 年",
    }


def _calc_intention_match(resume: dict[str, Any], jd: dict[str, Any]) -> dict[str, Any]:
    """
    计算求职意向匹配度。
    """
    job_int = (resume.get("job_intention") or "").strip()

    if not job_int:
        return {
            "dimension": "意向匹配",
            "weight": 0.10,
            "score": 60.0,
            "detail": "简历未填写求职意向，默认中等评分",
        }

    # 检查 JD 标题/描述中是否包含求职意向关键词
    jd_keywords = set(k.lower() for k in jd.get("keywords", []))
    intention_words = set(job_int.lower().split())

    overlap = jd_keywords & intention_words
    if overlap:
        return {
            "dimension": "意向匹配",
            "weight": 0.10,
            "score": 100.0,
            "detail": f"求职意向「{job_int}」与岗位相关 (匹配词: {', '.join(overlap)})",
        }

    return {
        "dimension": "意向匹配",
        "weight": 0.10,
        "score": 70.0,
        "detail": f"求职意向: {job_int}，未直接匹配到 JD 关键词",
    }
