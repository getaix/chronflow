"""提升测试覆盖率的补充测试。"""
import asyncio
import os
import signal
from datetime import datetime, timedelta

import pytest

from chronflow import Scheduler, SchedulerConfig, interval
from chronflow.decorators import set_global_scheduler
from chronflow.task import Task, TaskConfig, ScheduleType


class TestSchedulerSignalHandling:
    """测试调度器信号处理"""

    @pytest.mark.skipif(os.name == "nt", reason="Windows 不支持 Unix 信号")
    @pytest.mark.asyncio
    async def test_signal_handler_setup(self):
        """测试信号处理器是否正确设置"""
        scheduler = Scheduler()

        # 保存原始的信号处理器
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            # 启动调度器(会注册信号处理器)
            start_task = asyncio.create_task(scheduler.start(daemon=False))
            await asyncio.sleep(0.1)

            # 验证信号处理器已被修改
            current_sigint = signal.getsignal(signal.SIGINT)
            current_sigterm = signal.getsignal(signal.SIGTERM)

            assert current_sigint != original_sigint
            assert current_sigterm != original_sigterm

            # 停止调度器
            await scheduler.stop()
            await start_task
        finally:
            # 恢复原始信号处理器
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

    @pytest.mark.skipif(os.name != "nt", reason="仅在 Windows 上测试")
    def test_signal_handler_skipped_on_windows(self):
        """测试 Windows 上不设置信号处理器"""
        scheduler = Scheduler()

        # 在 Windows 上调用 _setup_signal_handlers 应该直接返回
        scheduler._setup_signal_handlers()
        # 不应该抛出异常

    @pytest.mark.asyncio
    async def test_scheduler_shutdown_event(self):
        """测试调度器关闭事件"""
        scheduler = Scheduler()

        # 启动调度器
        start_task = asyncio.create_task(scheduler.start(daemon=False))
        await asyncio.sleep(0.1)

        assert scheduler._running is True

        # 模拟信号触发关闭
        scheduler._shutdown_event.set()

        # 等待调度器停止
        await asyncio.sleep(0.2)

        assert scheduler._running is False
        await start_task


class TestDecoratorEdgeCases:
    """测试装饰器边界情况"""

    def teardown_method(self):
        """每个测试后清理全局调度器"""
        set_global_scheduler(None, clear_pending=True)

    @pytest.mark.asyncio
    async def test_decorator_function_still_callable(self):
        """测试装饰后的函数仍然可调用"""
        call_count = 0

        @interval(seconds=1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        # 函数应该仍然可调用
        result = await test_func()
        assert result == "result"
        assert call_count == 1

    def test_decorator_preserves_function_attributes(self):
        """测试装饰器保留函数属性"""

        @interval(seconds=1)
        async def test_func():
            """This is a test function"""
            pass

        # 函数的 __name__ 和 __doc__ 应该被保留
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "This is a test function"

    def test_task_attached_to_function(self):
        """测试任务对象被附加到函数上"""

        @interval(seconds=1)
        async def test_func():
            pass

        # 函数应该有 __chronflow_task__ 属性
        assert hasattr(test_func, "__chronflow_task__")
        assert test_func.__chronflow_task__.config.name == "test_func"


class TestConfigEdgeCases:
    """测试配置边界情况"""

    def test_config_from_nonexistent_file(self):
        """测试从不存在的文件加载配置"""
        from chronflow.config import SchedulerConfig

        with pytest.raises(FileNotFoundError):
            SchedulerConfig.from_file("nonexistent.json")

    def test_config_from_unsupported_format(self):
        """测试从不支持的格式加载配置"""
        from chronflow.config import SchedulerConfig
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            f.flush()
            with pytest.raises(ValueError, match="不支持的配置文件格式"):
                SchedulerConfig.from_file(f.name)
            os.unlink(f.name)


class TestTaskTimeout:
    """测试任务超时功能"""

    @pytest.mark.asyncio
    async def test_task_execution_with_timeout(self):
        """测试任务超时执行"""

        async def slow_task():
            await asyncio.sleep(2)
            return "completed"

        config = TaskConfig(
            name="slow_task",
            schedule_type=ScheduleType.ONCE,
            timeout=0.1,  # 100ms 超时
        )
        task = Task(func=slow_task, config=config)

        # 执行任务应该超时
        with pytest.raises(asyncio.TimeoutError):
            await task.execute()

        # 验证任务状态
        assert task.metrics.failed_runs == 1


class TestSchedulerRestart:
    """测试调度器重启功能"""

    @pytest.mark.asyncio
    async def test_scheduler_restart_non_daemon(self):
        """测试非守护模式的重启"""
        scheduler = Scheduler()

        async def dummy_task():
            pass

        # 注册一个任务
        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=1,
        )
        task = Task(func=dummy_task, config=config)
        scheduler.register_task(task)

        # 启动调度器
        start_task = asyncio.create_task(scheduler.start(daemon=False))
        await asyncio.sleep(0.1)
        assert scheduler._running is True

        # 停止调度器
        await scheduler.stop()
        await start_task
        assert scheduler._running is False

        # 重启调度器
        start_task = asyncio.create_task(scheduler.start(daemon=False))
        await asyncio.sleep(0.1)
        assert scheduler._running is True

        # 清理
        await scheduler.stop()
        await start_task


class TestSchedulerEdgeCases:
    """测试调度器边界情况"""

    @pytest.mark.asyncio
    async def test_schedule_ready_tasks_with_none_next_run(self):
        """测试 next_run_time 为 None 的情况"""

        async def dummy_task():
            pass

        scheduler = Scheduler()

        # 创建一个没有下次运行时间的任务
        # ONCE 类型但没有 start_time,next_run 会返回 None
        from datetime import timezone

        task_config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.ONCE,
            start_time=datetime.now(timezone.utc) - timedelta(days=1),  # 过去的时间
        )
        task = Task(func=dummy_task, config=task_config)
        scheduler.register_task(task)

        # 调用 _schedule_ready_tasks
        await scheduler.backend.connect()
        await scheduler._schedule_ready_tasks()
        await scheduler.backend.disconnect()

        # 任务的 next_run_time 应该被计算
        assert "test_task" in scheduler._task_next_run_times

    @pytest.mark.asyncio
    async def test_worker_handles_nonexistent_task(self):
        """测试 worker 处理不存在的任务"""
        from datetime import timezone

        scheduler = Scheduler()

        # 连接后端
        await scheduler.backend.connect()

        # 手动将一个不存在的任务放入队列
        await scheduler.backend.enqueue(
            task_id="nonexistent_task_id",
            task_name="nonexistent_task",
            scheduled_time=datetime.now(timezone.utc),
            payload={"task_name": "nonexistent_task"},
            priority=0,
        )

        # 启动调度器
        start_task = asyncio.create_task(scheduler.start(daemon=False))
        await asyncio.sleep(0.3)  # 给 worker 时间处理

        # 停止调度器
        await scheduler.stop()
        await start_task

        # 队列应该已清空(任务被拒绝)
        queue_size = await scheduler.backend.get_queue_size()
        assert queue_size == 0

        await scheduler.backend.disconnect()


class TestMetricsEdgeCases:
    """测试 metrics 边界情况"""

    def test_metrics_division_by_zero_protection(self):
        """测试除零保护"""
        from chronflow.metrics import MetricsCollector

        collector = MetricsCollector()

        # 不记录任何执行,直接获取统计
        stats = collector.get_stats()

        # 成功率应该是 0(而不是抛出除零异常)
        assert stats["success_rate"] == 0.0
        assert stats["average_duration"] == 0.0
        assert stats["executions_per_second"] == 0.0

    def test_metrics_task_stats_isolation(self):
        """测试不同任务的统计隔离"""
        from chronflow.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_task_execution("task1", success=True, duration=0.5)
        collector.record_task_execution("task2", success=False, duration=1.0)

        # 两个任务的统计应该是独立的
        assert collector.task_stats["task1"]["successes"] == 1
        assert collector.task_stats["task1"]["failures"] == 0

        assert collector.task_stats["task2"]["successes"] == 0
        assert collector.task_stats["task2"]["failures"] == 1


class TestLoggingAdapters:
    """测试日志适配器"""

    def test_structlog_adapter_with_exc_info(self):
        """测试 StructlogAdapter 处理 exc_info"""
        from chronflow.logging import StructlogAdapter

        adapter = StructlogAdapter()

        # 不应该抛出异常
        adapter.error("test error", exc_info=True)
        adapter.error("test error", test_key="test_value")


class TestLoggingExcInfo:
    """测试日志exc_info处理"""

    def test_stdlib_adapter_error_with_exc_info(self):
        """测试 StdlibAdapter 处理 exc_info 参数"""
        import logging
        from chronflow.logging import StdlibAdapter

        logger = logging.getLogger("test")
        adapter = StdlibAdapter(logger)

        # 不应该抛出异常
        adapter.error("test error", exc_info=True)
        adapter.error("test error", test_key="test_value", exc_info=False)

    def test_loguru_adapter_error_with_exc_info(self):
        """测试 LoguruAdapter 处理 exc_info 参数"""
        try:
            from loguru import logger
            from chronflow.logging import LoguruAdapter

            adapter = LoguruAdapter(logger)

            # 不应该抛出异常
            adapter.error("test error", exc_info=True)
            adapter.error("test error", test_key="test_value", exc_info=False)
        except ImportError:
            pytest.skip("loguru not installed")
