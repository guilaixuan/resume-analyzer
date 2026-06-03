"""
日志配置模块

输出到控制台（函数计算会自动采集到日志服务），
同时提供结构化日志格式便于排查。
"""

import logging
import sys


def setup_logger(name: str = "resume-api") -> logging.Logger:
    """
    配置并返回应用日志器。

    Args:
        name: 日志器名称

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger
