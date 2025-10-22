"""指标收集模块测试。"""

import asyncio
from datetime import datetime

import pytest

from chronflow.metrics import MetricsCollector
from chronflow.scheduler import Scheduler
from chronflow.task import ScheduleType, Task, TaskConfig


class TestMetricsCollector:
    """指标收集器测试类。"""

    def test_initial_state(self):
        """测试初始状态。"""
        collector = MetricsCollector()

        assert collector.total_executions == 0
        assert collector.successful_executions == 0
        assert collector.failed_executions == 0
        assert collector.total_duration == 0.0
        assert len(collector.task_stats) == 0

    def test_record_success(self):
        """测试记录成功执行。"""
        collector = MetricsCollector()

        collector.record_task_execution("task1", success=True, duration=1.5)

        assert collector.total_executions == 1
        assert collector.successful_executions == 1
        assert collector.failed_executions == 0
        assert collector.total_duration == 1.5

        # 检查任务级别统计
        assert "task1" in collector.task_stats
        stats = collector.task_stats["task1"]
        assert stats["executions"] == 1
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert stats["total_duration"] == 1.5
        assert stats["min_duration"] == 1.5
        assert stats["max_duration"] == 1.5

    def test_record_failure(self):
        """测试记录失败执行。"""
        collector = MetricsCollector()

        collector.record_task_execution("task1", success=False, duration=0.5)

        assert collector.total_executions == 1
        assert collector.successful_executions == 0
        assert collector.failed_executions == 1
        assert collector.total_duration == 0.5

        # 检查任务级别统计
        stats = collector.task_stats["task1"]
        assert stats["executions"] == 1
        assert stats["successes"] == 0
        assert stats["failures"] == 1

    def test_multiple_executions(self):
        """测试多次执行。"""
        collector = MetricsCollector()

        collector.record_task_execution("task1", success=True, duration=1.0)
        collector.record_task_execution("task1", success=True, duration=2.0)
        collector.record_task_execution("task1", success=False, duration=0.5)
        collector.record_task_execution("task2", success=True, duration=1.5)

        assert collector.total_executions == 4
        assert collector.successful_executions == 3
        assert collector.failed_executions == 1
        assert collector.total_duration == 5.0

        # task1 统计
        stats1 = collector.task_stats["task1"]
        assert stats1["executions"] == 3
        assert stats1["successes"] == 2
        assert stats1["failures"] == 1
        assert stats1["min_duration"] == 0.5
        assert stats1["max_duration"] == 2.0

        # task2 统计
        stats2 = collector.task_stats["task2"]
        assert stats2["executions"] == 1
        assert stats2["successes"] == 1

    def test_get_stats(self):
        """测试获取统计信息。"""
        collector = MetricsCollector()

        # 记录一些执行
        collector.record_task_execution("task1", success=True, duration=1.0)
        collector.record_task_execution("task1", success=False, duration=0.5)
        collector.record_task_execution("task2", success=True, duration=2.0)

        stats = collector.get_stats()

        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == pytest.approx(2 / 3)
        assert stats["total_duration"] == 3.5
        assert stats["average_duration"] == pytest.approx(3.5 / 3)
        assert "uptime_seconds" in stats
        assert "executions_per_second" in stats

        # 检查任务统计
        assert "task_stats" in stats
        task_stats = stats["task_stats"]
        assert "task1" in task_stats
        assert "task2" in task_stats

        # task1 详细统计
        task1_stats = task_stats["task1"]
        assert task1_stats["executions"] == 2
        assert task1_stats["average_duration"] == pytest.approx(0.75)
        assert task1_stats["success_rate"] == pytest.approx(0.5)

    def test_export_prometheus(self):
        """测试导出 Prometheus 格式。"""
        collector = MetricsCollector()

        collector.record_task_execution("test_task", success=True, duration=1.5)
        collector.record_task_execution("test_task", success=False, duration=0.5)

        prometheus_text = collector.export_prometheus()

        # 检查基本指标
        assert "chronflow_uptime_seconds" in prometheus_text
        assert "chronflow_executions_total 2" in prometheus_text
        assert "chronflow_executions_success 1" in prometheus_text
        assert "chronflow_executions_failed 1" in prometheus_text
        assert "chronflow_duration_seconds_total 2.0" in prometheus_text

        # 检查任务级别指标
        assert 'chronflow_task_executions{task="test_task"} 2' in prometheus_text
        assert 'task="test_task",stat="avg"' in prometheus_text
        assert 'task="test_task",stat="min"' in prometheus_text
        assert 'task="test_task",stat="max"' in prometheus_text

        # 检查 Prometheus 格式
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text

    def test_reset(self):
        """测试重置统计。"""
        collector = MetricsCollector()

        collector.record_task_execution("task1", success=True, duration=1.0)
        collector.record_task_execution("task2", success=False, duration=0.5)

        assert collector.total_executions == 2

        collector.reset()

        assert collector.total_executions == 0
        assert collector.successful_executions == 0
        assert collector.failed_executions == 0
        assert collector.total_duration == 0.0
        assert len(collector.task_stats) == 0

    def test_empty_stats(self):
        """测试空统计。"""
        collector = MetricsCollector()
        stats = collector.get_stats()

        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_duration"] == 0.0
        assert stats["executions_per_second"] >= 0

    def test_task_duration_tracking(self):
        """测试任务执行时长跟踪。"""
        collector = MetricsCollector()

        # 记录不同时长
        durations = [0.5, 1.0, 1.5, 2.0, 0.3]
        for duration in durations:
            collector.record_task_execution("task1", success=True, duration=duration)

        stats = collector.task_stats["task1"]
        assert stats["min_duration"] == 0.3
        assert stats["max_duration"] == 2.0
        assert stats["total_duration"] == sum(durations)


class TestSchedulerMetrics:
    """调度器指标集成测试类。"""

    @pytest.mark.asyncio
    async def test_scheduler_with_metrics(self):
        """测试启用指标的调度器。"""
        scheduler = Scheduler(enable_metrics=True)

        assert scheduler.metrics_collector is not None

        # 直接测试 metrics_collector
        scheduler.metrics_collector.record_task_execution(
            task_name="test_task",
            success=True,
            duration=1.5,
        )

        # 检查指标
        metrics = scheduler.get_metrics()
        assert metrics is not None
        assert metrics["total_executions"] == 1
        assert metrics["successful_executions"] == 1
        assert "test_task" in metrics["task_stats"]

    @pytest.mark.asyncio
    async def test_scheduler_without_metrics(self):
        """测试未启用指标的调度器。"""
        scheduler = Scheduler(enable_metrics=False)

        assert scheduler.metrics_collector is None

        metrics = scheduler.get_metrics()
        assert metrics is None

        prometheus_text = scheduler.export_prometheus_metrics()
        assert prometheus_text is None

    @pytest.mark.asyncio
    async def test_metrics_with_task_failure(self):
        """测试任务失败时的指标。"""
        scheduler = Scheduler(enable_metrics=True)

        # 直接记录失败指标
        scheduler.metrics_collector.record_task_execution(
            task_name="failing_task",
            success=False,
            duration=0.5,
        )

        # 检查失败指标
        metrics = scheduler.get_metrics()
        assert metrics is not None
        assert metrics["failed_executions"] == 1
        assert metrics["successful_executions"] == 0

    @pytest.mark.asyncio
    async def test_export_prometheus_from_scheduler(self):
        """测试从调度器导出 Prometheus 指标。"""
        scheduler = Scheduler(enable_metrics=True)

        # 记录一些指标
        scheduler.metrics_collector.record_task_execution(
            task_name="prometheus_task",
            success=True,
            duration=1.0,
        )

        prometheus_text = scheduler.export_prometheus_metrics()
        assert prometheus_text is not None
        assert "chronflow_executions_total" in prometheus_text
        assert 'task="prometheus_task"' in prometheus_text

    @pytest.mark.asyncio
    async def test_reset_metrics_from_scheduler(self):
        """测试从调度器重置指标。"""
        scheduler = Scheduler(enable_metrics=True)

        # 先记录一些指标
        scheduler.metrics_collector.record_task_execution(
            task_name="reset_task",
            success=True,
            duration=1.0,
        )
        scheduler.metrics_collector.record_task_execution(
            task_name="reset_task",
            success=False,
            duration=0.5,
        )

        # 重置前应该有执行记录
        metrics = scheduler.get_metrics()
        assert metrics is not None
        assert metrics["total_executions"] == 2

        # 重置
        scheduler.reset_metrics()

        # 重置后应该清零
        metrics_after = scheduler.get_metrics()
        assert metrics_after["total_executions"] == 0
        assert metrics_after["successful_executions"] == 0
        assert metrics_after["failed_executions"] == 0

    def test_metrics_with_multiple_tasks(self):
        """测试多任务指标收集。"""
        collector = MetricsCollector()

        # 模拟多个任务执行
        collector.record_task_execution("task1", success=True, duration=1.0)
        collector.record_task_execution("task2", success=True, duration=1.5)
        collector.record_task_execution("task3", success=False, duration=0.5)
        collector.record_task_execution("task1", success=True, duration=1.2)

        stats = collector.get_stats()

        # 检查总体统计
        assert stats["total_executions"] == 4
        assert stats["successful_executions"] == 3
        assert stats["failed_executions"] == 1

        # 检查各任务统计
        task_stats = stats["task_stats"]
        assert len(task_stats) == 3
        assert task_stats["task1"]["executions"] == 2
        assert task_stats["task2"]["executions"] == 1
        assert task_stats["task3"]["executions"] == 1
