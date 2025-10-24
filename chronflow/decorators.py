"""简洁易用的装饰器 API,用于快速定义定时任务。"""

from __future__ import annotations

import threading
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from chronflow.retry import RetryPolicy
from chronflow.task import ScheduleType, Task, TaskConfig

P = ParamSpec("P")
T = TypeVar("T")

# 全局调度器引用(用于装饰器)
_global_scheduler: Any | None = None
_pending_tasks: list[Task] = []
_scheduler_lock = threading.RLock()  # 可重入锁,保护全局状态


def set_global_scheduler(scheduler: Any | None, *, clear_pending: bool = False) -> None:
    """设置或清除全局调度器实例。

    参数:
        scheduler: 调度器实例
        clear_pending: 在清除全局调度器时是否清空待注册任务

    线程安全:
        使用可重入锁保护全局状态,确保多线程环境下的安全性
    """
    global _global_scheduler

    with _scheduler_lock:
        _global_scheduler = scheduler

        if scheduler is None:
            if clear_pending:
                _pending_tasks.clear()
            return

        # 安全地转移待注册任务(在锁内复制列表)
        tasks_to_register = list(_pending_tasks)
        _pending_tasks.clear()

    # 在锁外注册任务,避免在调度器注册时可能的死锁
    for task in tasks_to_register:
        try:
            scheduler.register_task(task)
        except ValueError:
            # 如果名称冲突,跳过即可
            continue


def get_global_scheduler() -> Any:
    """获取全局调度器实例。

    返回值:
        调度器实例

    抛出:
        RuntimeError: 未设置全局调度器

    线程安全:
        使用锁保护读取操作,确保线程安全
    """
    with _scheduler_lock:
        if _global_scheduler is None:
            raise RuntimeError(
                "未设置全局调度器。请先调用 set_global_scheduler() 或使用 Scheduler 实例"
            )
        return _global_scheduler


def scheduled(
    *,
    name: str | None = None,
    cron: str | None = None,
    interval: float | timedelta | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    max_instances: int = 1,
    timeout: float | None = None,
    retry_policy: RetryPolicy | None = None,
    enabled: bool = True,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """通用定时任务装饰器。

    参数:
        name: 任务名称(默认使用函数名)
        cron: Cron 表达式
        interval: 间隔时间(秒或 timedelta)
        start_time: 开始时间
        end_time: 结束时间
        max_instances: 最大并发实例数
        timeout: 超时时间(秒)
        retry_policy: 重试策略
        enabled: 是否启用
        tags: 标签列表
        metadata: 元数据

    返回值:
        装饰器函数

    示例:
        @scheduled(cron="*/5 * * * * *")  # 每5秒执行
        async def my_task():
            print("执行任务")

        @scheduled(interval=60, retry_policy=RetryPolicy.aggressive())
        async def another_task():
            print("每60秒执行一次")
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        # 确定任务名称
        task_name = name or func.__name__

        # 确定调度类型和参数
        if cron is not None:
            schedule_type = ScheduleType.CRON
            cron_expression = cron
            interval_seconds = None
        elif interval is not None:
            schedule_type = ScheduleType.INTERVAL
            cron_expression = None
            if isinstance(interval, timedelta):
                interval_seconds = interval.total_seconds()
            else:
                interval_seconds = float(interval)
        else:
            schedule_type = ScheduleType.ONCE
            cron_expression = None
            interval_seconds = None

        # 创建任务配置
        config = TaskConfig(
            name=task_name,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            start_time=start_time,
            end_time=end_time,
            max_instances=max_instances,
            timeout=timeout,
            retry_policy=retry_policy or RetryPolicy.default(),
            enabled=enabled,
            tags=tags or [],
            metadata=metadata or {},
        )

        # 创建任务实例
        task = Task(func=func, config=config)

        # 自动注册到全局调度器(如果存在)- 需要锁保护
        with _scheduler_lock:
            if _global_scheduler is not None:
                try:
                    _global_scheduler.register_task(task)
                except ValueError:
                    # 任务名称冲突,跳过(说明已经注册过了)
                    pass
            else:
                # 全局调度器未设置,记录为待注册任务
                # 检查是否已经在待注册列表中(避免重复)
                if not any(t.config.name == task_name for t in _pending_tasks):
                    _pending_tasks.append(task)

        # 保存任务引用到函数属性
        func.__chronflow_task__ = task  # type: ignore

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def cron(
    expression: str,
    *,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """Cron 表达式定时任务装饰器。

    参数:
        expression: Cron 表达式(支持秒级)
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @cron("*/10 * * * * *")  # 每10秒执行
        async def sync_data():
            await fetch_and_sync()

        @cron("0 0 * * *")  # 每天零点执行
        async def daily_cleanup():
            await cleanup_old_data()
    """
    return scheduled(
        cron=expression,
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def interval(
    seconds: float | timedelta,
    *,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """固定间隔定时任务装饰器。

    参数:
        seconds: 间隔秒数或 timedelta
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @interval(30)  # 每30秒执行
        async def check_health():
            await ping_services()

        @interval(timedelta(hours=1))  # 每小时执行
        async def hourly_report():
            await generate_report()
    """
    return scheduled(
        interval=seconds,
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def once(
    at: datetime,
    *,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """一次性定时任务装饰器。

    参数:
        at: 执行时间
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @once(datetime(2024, 12, 31, 23, 59, 59))
        async def new_year_task():
            print("新年快乐!")
    """
    return scheduled(
        start_time=at,
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def every(
    seconds: float | None = None,
    minutes: float | None = None,
    hours: float | None = None,
    days: float | None = None,
    *,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """更直观的间隔任务装饰器。

    参数:
        seconds: 秒数
        minutes: 分钟数
        hours: 小时数
        days: 天数
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @every(minutes=30)  # 每 30 分钟
        async def half_hourly_task():
            print("每 30 分钟执行")

        @every(hours=2, minutes=30)  # 每 2.5 小时
        async def custom_interval():
            print("每 2.5 小时执行")
    """
    total_seconds = 0.0

    if seconds:
        total_seconds += seconds
    if minutes:
        total_seconds += minutes * 60
    if hours:
        total_seconds += hours * 3600
    if days:
        total_seconds += days * 86400

    if total_seconds == 0:
        raise ValueError("必须指定至少一个时间单位")

    return interval(
        total_seconds,
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def hourly(
    *,
    minute: int = 0,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """每小时执行的任务装饰器。

    参数:
        minute: 在第几分钟执行 (0-59),默认为整点
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @hourly()  # 每小时整点执行
        async def hourly_task():
            print("每小时执行")

        @hourly(minute=30)  # 每小时的第 30 分钟执行
        async def half_past():
            print("每小时 30 分执行")
    """
    if not 0 <= minute <= 59:
        raise ValueError("minute 必须在 0-59 之间")

    return cron(
        f"0 {minute} * * * *",
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def daily(
    *,
    hour: int = 0,
    minute: int = 0,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """每天执行的任务装饰器。

    参数:
        hour: 小时 (0-23),默认为 0 点
        minute: 分钟 (0-59),默认为 0 分
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @daily(hour=9, minute=30)  # 每天 9:30
        async def morning_task():
            print("早上 9:30 执行")

        @daily()  # 每天 0:00
        async def midnight_task():
            print("每天午夜执行")
    """
    if not 0 <= hour <= 23:
        raise ValueError("hour 必须在 0-23 之间")
    if not 0 <= minute <= 59:
        raise ValueError("minute 必须在 0-59 之间")

    return cron(
        f"0 {minute} {hour} * * *",
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def weekly(
    *,
    day: int = 0,
    hour: int = 0,
    minute: int = 0,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """每周执行的任务装饰器。

    参数:
        day: 星期几 (0=周日, 1=周一, ..., 6=周六),默认为周日
        hour: 小时 (0-23)
        minute: 分钟 (0-59)
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @weekly(day=1, hour=9)  # 每周一 9:00
        async def weekly_report():
            print("周一报表")

        @weekly(day=5, hour=18)  # 每周五 18:00
        async def tgif():
            print("周五晚上!")
    """
    if not 0 <= day <= 6:
        raise ValueError("day 必须在 0-6 之间 (0=周日, 1=周一, ..., 6=周六)")
    if not 0 <= hour <= 23:
        raise ValueError("hour 必须在 0-23 之间")
    if not 0 <= minute <= 59:
        raise ValueError("minute 必须在 0-59 之间")

    return cron(
        f"0 {minute} {hour} * * {day}",
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )


def monthly(
    *,
    day: int = 1,
    hour: int = 0,
    minute: int = 0,
    name: str | None = None,
    retry_policy: RetryPolicy | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """每月执行的任务装饰器。

    参数:
        day: 几号 (1-31),默认为 1 号
        hour: 小时 (0-23)
        minute: 分钟 (0-59)
        name: 任务名称
        retry_policy: 重试策略
        timeout: 超时时间
        **kwargs: 其他参数

    返回值:
        装饰器函数

    示例:
        @monthly(day=1, hour=0)  # 每月 1 号 0:00
        async def monthly_cleanup():
            print("月初清理")

        @monthly(day=15)  # 每月 15 号 0:00
        async def mid_month():
            print("月中任务")
    """
    if not 1 <= day <= 31:
        raise ValueError("day 必须在 1-31 之间")
    if not 0 <= hour <= 23:
        raise ValueError("hour 必须在 0-23 之间")
    if not 0 <= minute <= 59:
        raise ValueError("minute 必须在 0-59 之间")

    return cron(
        f"0 {minute} {hour} {day} * *",
        name=name,
        retry_policy=retry_policy,
        timeout=timeout,
        **kwargs,
    )
