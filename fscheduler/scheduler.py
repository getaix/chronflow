"""核心调度器实现,负责任务调度和执行管理。"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fscheduler.backends.base import QueueBackend
from fscheduler.backends.memory import MemoryBackend
from fscheduler.config import SchedulerConfig
from fscheduler.logging import LoggerAdapter, get_default_logger
from fscheduler.metrics import MetricsCollector
from fscheduler.task import Task, TaskStatus


class Scheduler:
    """高性能异步任务调度器。

    特性:
    - 支持秒级精度的定时任务
    - 可插拔的后端存储(内存/Redis/RabbitMQ/SQLite)
    - 可插拔的日志系统(structlog/loguru/stdlib)
    - 优雅关闭和信号处理
    - 自动重试机制
    - 任务优先级和并发控制
    """

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        backend: QueueBackend | None = None,
        logger: LoggerAdapter | None = None,
        enable_metrics: bool = False,
    ) -> None:
        """初始化调度器。

        参数:
            config: 调度器配置,默认使用 SchedulerConfig()
            backend: 队列后端,默认使用 MemoryBackend
            logger: 日志适配器,默认使用 structlog
            enable_metrics: 是否启用性能指标收集
        """
        self.config = config or SchedulerConfig()
        self.backend = backend or MemoryBackend(max_size=self.config.queue_size)

        # 任务管理
        self._tasks: dict[str, Task] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._worker_tasks: set[asyncio.Task[None]] = set()

        # 配置日志
        if logger:
            self._log = logger
        elif self.config.enable_logging:
            self._log = get_default_logger()
        else:
            from fscheduler.logging import NoOpAdapter

            self._log = NoOpAdapter()

        # 配置指标收集
        self.metrics_collector = MetricsCollector() if enable_metrics else None

    def set_logger(self, logger: LoggerAdapter) -> None:
        """设置日志适配器。

        参数:
            logger: 日志适配器实例

        示例:
            from loguru import logger
            from fscheduler.logging import LoguruAdapter

            scheduler.set_logger(LoguruAdapter(logger))
        """
        self._log = logger

    def register_task(self, task: Task) -> None:
        """注册任务到调度器。

        参数:
            task: 要注册的任务实例

        抛出:
            ValueError: 任务名称已存在
        """
        task_name = task.config.name

        if task_name in self._tasks:
            raise ValueError(f"任务 '{task_name}' 已存在")

        self._tasks[task_name] = task
        self._log.info("任务已注册", task_name=task_name, task_id=task.id)

    def unregister_task(self, task_name: str) -> None:
        """注销任务。

        参数:
            task_name: 任务名称
        """
        if task_name in self._tasks:
            del self._tasks[task_name]
            self._log.info("任务已注销", task_name=task_name)

    def get_task(self, task_name: str) -> Task | None:
        """获取任务实例。

        参数:
            task_name: 任务名称

        返回值:
            任务实例,如果不存在返回 None
        """
        return self._tasks.get(task_name)

    async def start(self, daemon: bool = False) -> None:
        """启动调度器。

        参数:
            daemon: 是否以守护进程模式运行
        """
        if self._running:
            self._log.warning("调度器已在运行")
            return

        self._running = True
        self._shutdown_event.clear()

        # 连接后端
        await self.backend.connect()
        health_ok = await self.backend.health_check()

        if not health_ok:
            raise RuntimeError("后端健康检查失败")

        self._log.info(
            "调度器启动",
            backend=self.backend.__class__.__name__,
            max_workers=self.config.max_workers,
            queue_size=self.config.queue_size,
        )

        # 启动任务调度循环
        scheduler_task = asyncio.create_task(self._schedule_loop())

        # 启动工作协程池
        for i in range(self.config.max_workers):
            worker_task = asyncio.create_task(self._worker_loop(i))
            self._worker_tasks.add(worker_task)
            worker_task.add_done_callback(self._worker_tasks.discard)

        # 注册信号处理
        if daemon:
            self._register_signal_handlers()

        try:
            # 等待关闭信号
            await self._shutdown_event.wait()
        finally:
            # 停止调度循环
            scheduler_task.cancel()

            # 等待工作协程完成
            await self._shutdown_workers()

            # 断开后端连接
            await self.backend.disconnect()

            self._running = False
            self._log.info("调度器已停止")

    async def stop(self) -> None:
        """停止调度器。"""
        if not self._running:
            return

        self._log.info("正在停止调度器...")
        self._shutdown_event.set()

    async def _schedule_loop(self) -> None:
        """任务调度主循环,负责将任务放入队列。"""
        self._log.info("调度循环启动")

        while self._running:
            try:
                await self._schedule_ready_tasks()
                await asyncio.sleep(0.1)  # 每 100ms 检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("调度循环错误", error=str(e), exc_info=True)
                await asyncio.sleep(1)

        self._log.info("调度循环停止")

    async def _schedule_ready_tasks(self) -> None:
        """检查并调度就绪的任务。"""
        now = datetime.now()

        for task in self._tasks.values():
            if not task.config.enabled or task.is_cancelled():
                continue

            # 计算下次运行时间
            next_run = task.config.get_next_run_time()

            if next_run and next_run <= now:
                # 将任务加入队列
                try:
                    await self.backend.enqueue(
                        task_id=task.id,
                        task_name=task.config.name,
                        scheduled_time=next_run,
                        payload={
                            "task_name": task.config.name,
                            "scheduled_time": next_run.isoformat(),
                        },
                        priority=0,
                    )

                    self._log.debug(
                        "任务已加入队列",
                        task_name=task.config.name,
                        next_run=next_run.isoformat(),
                    )

                except Exception as e:
                    self._log.error(
                        "任务入队失败",
                        task_name=task.config.name,
                        error=str(e),
                    )

    async def _worker_loop(self, worker_id: int) -> None:
        """工作协程,负责从队列取出任务并执行。

        参数:
            worker_id: 工作协程 ID
        """
        self._log.info("工作协程启动", worker_id=worker_id)

        while self._running:
            try:
                # 从队列获取任务
                tasks = await self.backend.dequeue(limit=1)

                if not tasks:
                    await asyncio.sleep(0.5)
                    continue

                task_data = tasks[0]
                task_name = task_data["task_name"]
                task_id = task_data["task_id"]

                task = self._tasks.get(task_name)

                if not task:
                    self._log.warning("任务不存在", task_name=task_name)
                    await self.backend.reject(task_id)
                    continue

                # 执行任务
                try:
                    self._log.info("开始执行任务", task_name=task_name, worker_id=worker_id)

                    # 记录开始时间
                    import time
                    start_time = time.time()

                    await task.execute()
                    await self.backend.acknowledge(task_id)

                    # 记录执行指标
                    execution_time = time.time() - start_time
                    if self.metrics_collector:
                        self.metrics_collector.record_task_execution(
                            task_name=task_name,
                            success=True,
                            duration=execution_time,
                        )

                    self._log.info(
                        "任务执行成功",
                        task_name=task_name,
                        worker_id=worker_id,
                        metrics=task.metrics.model_dump(),
                    )

                except Exception as e:
                    await self.backend.reject(task_id, requeue=False)

                    # 记录失败指标
                    execution_time = time.time() - start_time
                    if self.metrics_collector:
                        self.metrics_collector.record_task_execution(
                            task_name=task_name,
                            success=False,
                            duration=execution_time,
                        )

                    self._log.error(
                        "任务执行失败",
                        task_name=task_name,
                        worker_id=worker_id,
                        error=str(e),
                        exc_info=True,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error(
                    "工作协程错误",
                    worker_id=worker_id,
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(1)

        self._log.info("工作协程停止", worker_id=worker_id)

    async def _shutdown_workers(self) -> None:
        """优雅关闭所有工作协程。"""
        self._log.info("正在关闭工作协程...")

        # 取消所有工作任务
        for task in self._worker_tasks:
            task.cancel()

        # 等待所有任务完成或超时
        if self._worker_tasks:
            await asyncio.wait(
                self._worker_tasks,
                timeout=self.config.shutdown_timeout,
            )

        self._log.info("所有工作协程已关闭")

    def _register_signal_handlers(self) -> None:
        """注册系统信号处理器。"""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.stop()),
            )

        self._log.info("信号处理器已注册")

    @asynccontextmanager
    async def run_context(self) -> AsyncIterator[Scheduler]:
        """使用上下文管理器运行调度器。

        示例:
            async with scheduler.run_context():
                # 调度器在这里运行
                await asyncio.sleep(60)
            # 自动停止调度器
        """
        try:
            # 启动调度器(非守护模式)
            start_task = asyncio.create_task(self.start(daemon=False))
            await asyncio.sleep(0.1)  # 等待启动完成

            yield self
        finally:
            await self.stop()
            await start_task

    async def get_stats(self) -> dict[str, Any]:
        """获取调度器统计信息。

        返回值:
            包含统计信息的字典
        """
        queue_size = await self.backend.get_queue_size()

        task_stats = []
        for task in self._tasks.values():
            task_stats.append(
                {
                    "name": task.config.name,
                    "status": task.status.value,
                    "metrics": task.metrics.model_dump(),
                }
            )

        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "queue_size": queue_size,
            "active_workers": len(self._worker_tasks),
            "max_workers": self.config.max_workers,
            "backend": self.backend.__class__.__name__,
            "tasks": task_stats,
        }

    def list_tasks(self) -> list[dict[str, Any]]:
        """获取所有任务列表。

        返回值:
            任务信息列表

        示例:
            tasks = scheduler.list_tasks()
            for task_info in tasks:
                print(f"{task_info['name']}: {task_info['status']}")
        """
        return [
            {
                "id": task.id,
                "name": task.config.name,
                "status": task.status.value,
                "schedule_type": task.config.schedule_type.value,
                "enabled": task.config.enabled,
                "total_runs": task.metrics.total_runs,
                "successful_runs": task.metrics.successful_runs,
                "failed_runs": task.metrics.failed_runs,
                "success_rate": (
                    task.metrics.successful_runs / task.metrics.total_runs * 100
                    if task.metrics.total_runs > 0
                    else 0.0
                ),
                "average_execution_time": task.metrics.average_execution_time,
                "consecutive_failures": task.metrics.consecutive_failures,
            }
            for task in self._tasks.values()
        ]

    def get_task_count(self) -> dict[str, int]:
        """获取各状态任务数量统计。

        返回值:
            任务数量统计字典

        示例:
            counts = scheduler.get_task_count()
            print(f"运行中: {counts['running']}")
            print(f"失败: {counts['failed']}")
        """
        counts = {
            "total": len(self._tasks),
            "enabled": 0,
            "disabled": 0,
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0,
            "cancelled": 0,
        }

        for task in self._tasks.values():
            if task.config.enabled:
                counts["enabled"] += 1
            else:
                counts["disabled"] += 1

            status_key = task.status.value
            if status_key in counts:
                counts[status_key] += 1

        return counts

    def get_task_by_status(self, status: TaskStatus) -> list[Task]:
        """根据状态获取任务列表。

        参数:
            status: 任务状态

        返回值:
            符合状态的任务列表

        示例:
            failed_tasks = scheduler.get_task_by_status(TaskStatus.FAILED)
            for task in failed_tasks:
                print(f"失败任务: {task.config.name}")
        """
        return [task for task in self._tasks.values() if task.status == status]

    def get_task_by_tag(self, tag: str) -> list[Task]:
        """根据标签获取任务列表。

        参数:
            tag: 标签名称

        返回值:
            包含该标签的任务列表

        示例:
            critical_tasks = scheduler.get_task_by_tag("critical")
        """
        return [task for task in self._tasks.values() if tag in task.config.tags]

    async def pause_task(self, task_name: str) -> bool:
        """暂停任务(禁用)。

        参数:
            task_name: 任务名称

        返回值:
            是否成功暂停

        示例:
            await scheduler.pause_task("my_task")
        """
        task = self._tasks.get(task_name)
        if task:
            task.config.enabled = False
            self._log.info("任务已暂停", task_name=task_name)
            return True
        return False

    async def resume_task(self, task_name: str) -> bool:
        """恢复任务(启用)。

        参数:
            task_name: 任务名称

        返回值:
            是否成功恢复

        示例:
            await scheduler.resume_task("my_task")
        """
        task = self._tasks.get(task_name)
        if task:
            task.config.enabled = True
            self._log.info("任务已恢复", task_name=task_name)
            return True
        return False

    def get_metrics(self) -> dict[str, Any] | None:
        """获取性能指标。

        返回值:
            性能指标字典,如果未启用指标收集则返回 None

        示例:
            if scheduler.metrics_collector:
                metrics = scheduler.get_metrics()
                print(f"总执行次数: {metrics['total_executions']}")
                print(f"成功率: {metrics['success_rate']:.2%}")
        """
        if not self.metrics_collector:
            return None
        return self.metrics_collector.get_stats()

    def export_prometheus_metrics(self) -> str | None:
        """导出 Prometheus 格式的指标。

        返回值:
            Prometheus 格式的指标文本,如果未启用指标收集则返回 None

        示例:
            metrics_text = scheduler.export_prometheus_metrics()
            if metrics_text:
                # 可以通过 HTTP 端点暴露给 Prometheus
                print(metrics_text)
        """
        if not self.metrics_collector:
            return None
        return self.metrics_collector.export_prometheus()

    def reset_metrics(self) -> None:
        """重置性能指标。

        示例:
            scheduler.reset_metrics()
        """
        if self.metrics_collector:
            self.metrics_collector.reset()
            self._log.info("性能指标已重置")

    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"Scheduler(tasks={len(self._tasks)}, "
            f"running={self._running}, "
            f"backend={self.backend.__class__.__name__})"
        )
