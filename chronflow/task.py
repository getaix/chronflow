"""任务模型和执行逻辑。"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, ParamSpec, TypeVar

from croniter import croniter
from pydantic import BaseModel, Field

from chronflow.config import TaskMetrics
from chronflow.retry import RetryPolicy

P = ParamSpec("P")
T = TypeVar("T")


class TaskStatus(str, Enum):
    """任务执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class ScheduleType(str, Enum):
    """任务调度类型。"""

    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


class TaskConfig(BaseModel):
    """定时任务配置。"""

    name: str = Field(
        description="唯一的任务名称",
    )

    schedule_type: ScheduleType = Field(
        description="调度类型",
    )

    interval_seconds: float | None = Field(
        default=None,
        ge=0.1,
        description="基于间隔的任务的间隔秒数",
    )

    cron_expression: str | None = Field(
        default=None,
        description="基于 Cron 的任务的 Cron 表达式",
    )

    start_time: datetime | None = Field(
        default=None,
        description="任务开始时间",
    )

    end_time: datetime | None = Field(
        default=None,
        description="任务结束时间",
    )

    max_instances: int = Field(
        default=1,
        ge=1,
        description="该任务的最大并发实例数",
    )

    timeout: float | None = Field(
        default=None,
        gt=0,
        description="任务执行超时时间(秒)",
    )

    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy.default,
        description="失败任务的重试策略",
    )

    enabled: bool = Field(
        default=True,
        description="任务是否启用",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="任务分类标签",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="附加元数据",
    )

    def get_next_run_time(
        self, after: datetime | None = None, use_timezone: timezone | str | None = None
    ) -> datetime | None:
        """根据调度计算下次运行时间。

        参数:
            after: 参考时间点,默认使用当前时间
            use_timezone: 使用的时区,可以是timezone对象、ZoneInfo字符串或None(使用UTC)

        注意:
            - 返回时区感知的datetime以确保与调度器的时间比较一致
            - 如果传入的after无时区信息,会自动添加指定的时区
        """
        # 确定使用的时区
        if use_timezone is None:
            tz = timezone.utc
        elif isinstance(use_timezone, str):
            from zoneinfo import ZoneInfo

            try:
                tz = ZoneInfo(use_timezone)
            except Exception:
                tz = timezone.utc
        else:
            tz = use_timezone

        if after is not None:
            # 如果传入时间无时区信息,添加指定时区
            now = after if after.tzinfo is not None else after.replace(tzinfo=tz)
        else:
            # 使用指定时区获取当前时间
            now = datetime.now(tz)

        # 检查任务是否在时间范围内
        if self.start_time:
            start = self.start_time if self.start_time.tzinfo is not None else self.start_time.replace(tzinfo=timezone.utc)
            if now < start:
                return start

        if self.end_time:
            end = self.end_time if self.end_time.tzinfo is not None else self.end_time.replace(tzinfo=timezone.utc)
            if now >= end:
                return None

        if self.schedule_type == ScheduleType.ONCE:
            if self.start_time:
                start = self.start_time if self.start_time.tzinfo is not None else self.start_time.replace(tzinfo=timezone.utc)
                return start if start > now else None
            return None

        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.interval_seconds is None:
                raise ValueError("interval_seconds required for INTERVAL schedule")

            next_run = now + timedelta(seconds=self.interval_seconds)
            if self.end_time:
                end = self.end_time if self.end_time.tzinfo is not None else self.end_time.replace(tzinfo=timezone.utc)
                if next_run > end:
                    return None
            return next_run

        elif self.schedule_type == ScheduleType.CRON:
            if self.cron_expression is None:
                raise ValueError("cron_expression required for CRON schedule")

            cron = croniter(self.cron_expression, now)
            next_run = cron.get_next(datetime)

            # croniter可能返回无时区信息的datetime,确保添加时区
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            if self.end_time:
                end = self.end_time if self.end_time.tzinfo is not None else self.end_time.replace(tzinfo=timezone.utc)
                if next_run > end:
                    return None
            return next_run

        return None


class Task:
    """表示一个带有执行逻辑的定时任务。"""

    def __init__(
        self,
        func: Callable[P, Coroutine[Any, Any, T]],
        config: TaskConfig,
    ) -> None:
        """初始化任务。

        参数:
            func: 要执行的异步函数
            config: 任务配置
        """
        self.id = str(uuid.uuid4())
        self.func = func
        self.config = config
        self.status = TaskStatus.PENDING
        self.metrics = TaskMetrics()
        self._running_instances = 0
        self._cancel_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def execute(self, *args: P.args, **kwargs: P.kwargs) -> T | None:
        """使用重试逻辑执行任务。"""
        if not self.config.enabled:
            return None

        async with self._lock:
            if self._running_instances >= self.config.max_instances:
                return None
            self._running_instances += 1

        start_time = time.perf_counter()
        self.status = TaskStatus.RUNNING

        try:
            # 如果指定了超时时间则使用超时执行
            if self.config.timeout:
                result = await asyncio.wait_for(
                    self._execute_with_retry(*args, **kwargs),
                    timeout=self.config.timeout,
                )
            else:
                result = await self._execute_with_retry(*args, **kwargs)

            # 更新指标
            execution_time = time.perf_counter() - start_time
            self.metrics.update_success(execution_time)
            self.status = TaskStatus.COMPLETED

            return result

        except TimeoutError:
            execution_time = time.perf_counter() - start_time
            self.metrics.update_failure(execution_time)
            self.status = TaskStatus.FAILED
            raise

        except Exception:
            execution_time = time.perf_counter() - start_time
            self.metrics.update_failure(execution_time)
            self.status = TaskStatus.FAILED
            raise

        finally:
            async with self._lock:
                self._running_instances -= 1

    async def _execute_with_retry(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """使用重试逻辑执行函数。"""
        retryer = self.config.retry_policy.create_retryer()

        async for attempt in retryer:
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    self.status = TaskStatus.RETRYING

                result = await self.func(*args, **kwargs)
                return result

        # 由于重新抛出异常,此处不应被执行到,但为了类型检查而保留
        raise RuntimeError("重试逻辑意外失败")

    async def cancel(self) -> None:
        """取消任务。"""
        self.status = TaskStatus.CANCELLED
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """检查任务是否已被取消。"""
        return self._cancel_event.is_set()

    def __repr__(self) -> str:
        """任务的字符串表示形式。"""
        return (
            f"Task(id={self.id[:8]}, name={self.config.name}, "
            f"status={self.status}, runs={self.metrics.total_runs})"
        )
