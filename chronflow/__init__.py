"""
chronflow - 高性能异步任务调度库,专为 Python 3.11+ 设计

特性:
- 基于 asyncio 的异步/等待支持
- 秒级精度的 Cron 风格调度
- 指数退避的任务重试机制
- 配置文件支持(YAML, JSON, TOML)
- 可插拔的日志系统(structlog, loguru, stdlib)
- 低内存占用和高性能
- 后台守护进程支持
- 完整的类型提示,保证类型安全
- 丰富的监控和任务管理功能
"""

from chronflow.backends import create_backend, get_registered_backends, register_backend
from chronflow.config import SchedulerConfig
from chronflow.decorators import (
    cron,
    daily,
    every,
    hourly,
    interval,
    monthly,
    once,
    scheduled,
    weekly,
)
from chronflow.logging import (
    LoggerAdapter,
    LoguruAdapter,
    NoOpAdapter,
    StdlibAdapter,
    StructlogAdapter,
)
from chronflow.metrics import MetricsCollector
from chronflow.retry import RetryPolicy
from chronflow.scheduler import Scheduler
from chronflow.task import Task, TaskConfig, TaskStatus

__version__ = "0.2.1"
__all__ = [
    # 核心组件
    "Scheduler",
    "Task",
    "TaskConfig",
    "TaskStatus",
    "SchedulerConfig",
    "RetryPolicy",
    "MetricsCollector",
    # 后端注册
    "register_backend",
    "get_registered_backends",
    "create_backend",
    # 装饰器
    "scheduled",
    "interval",
    "cron",
    "once",
    "every",
    "hourly",
    "daily",
    "weekly",
    "monthly",
    # 日志适配器
    "LoggerAdapter",
    "StructlogAdapter",
    "LoguruAdapter",
    "StdlibAdapter",
    "NoOpAdapter",
]
