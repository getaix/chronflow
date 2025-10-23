"""任务模块测试。"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from chronflow.retry import RetryPolicy
from chronflow.task import ScheduleType, Task, TaskConfig, TaskStatus


class TestTaskConfig:
    """任务配置测试类。"""

    def test_interval_task_config(self):
        """测试间隔任务配置。"""
        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        assert config.name == "test_task"
        assert config.schedule_type == ScheduleType.INTERVAL
        assert config.interval_seconds == 10.0
        assert config.enabled is True

    def test_cron_task_config(self):
        """测试 Cron 任务配置。"""
        config = TaskConfig(
            name="cron_task",
            schedule_type=ScheduleType.CRON,
            cron_expression="*/5 * * * * *",
        )

        assert config.name == "cron_task"
        assert config.schedule_type == ScheduleType.CRON
        assert config.cron_expression == "*/5 * * * * *"

    def test_once_task_config(self):
        """测试一次性任务配置。"""
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)

        config = TaskConfig(
            name="once_task",
            schedule_type=ScheduleType.ONCE,
            start_time=start_time,
        )

        assert config.name == "once_task"
        assert config.schedule_type == ScheduleType.ONCE
        assert config.start_time == start_time

    def test_get_next_run_time_interval(self):
        """测试间隔任务的下次运行时间。"""
        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        now = datetime.now(timezone.utc)
        next_run = config.get_next_run_time(after=now)

        assert next_run is not None
        assert next_run > now
        assert (next_run - now).total_seconds() == pytest.approx(10.0, abs=0.1)

    def test_get_next_run_time_cron(self):
        """测试 Cron 任务的下次运行时间。"""
        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 0 * * * *",  # 每小时整点
        )

        now = datetime.now(timezone.utc)
        next_run = config.get_next_run_time(after=now)

        assert next_run is not None
        assert next_run > now
        assert next_run.minute == 0
        assert next_run.second == 0

    def test_get_next_run_time_once_future(self):
        """测试未来一次性任务的下次运行时间。"""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.ONCE,
            start_time=future_time,
        )

        next_run = config.get_next_run_time()

        assert next_run == future_time

    def test_get_next_run_time_once_past(self):
        """测试过去一次性任务的下次运行时间。"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.ONCE,
            start_time=past_time,
        )

        next_run = config.get_next_run_time()

        assert next_run is None

    def test_get_next_run_time_with_end_time(self):
        """测试带结束时间的任务。"""
        end_time = datetime.now(timezone.utc) - timedelta(hours=1)

        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            end_time=end_time,
        )

        next_run = config.get_next_run_time()

        assert next_run is None

    def test_get_next_run_time_interval_exceeds_end_time(self):
        """测试间隔任务超过结束时间。"""
        # 设置结束时间为当前时间后 5 秒
        end_time = datetime.now(timezone.utc) + timedelta(seconds=5)

        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,  # 下次运行将超过结束时间
            end_time=end_time,
        )

        # 从当前时间计算下次运行
        next_run = config.get_next_run_time()

        # 由于下次运行(当前+10秒)超过了结束时间(当前+5秒),应该返回 None
        assert next_run is None

    def test_get_next_run_time_cron_exceeds_end_time(self):
        """测试 Cron 任务超过结束时间。"""
        # 设置结束时间为当前时间后 30 秒
        end_time = datetime.now(timezone.utc) + timedelta(seconds=30)

        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 0 * * * *",  # 每小时整点(至少 30 分钟后)
            end_time=end_time,
        )

        # 从当前时间计算下次运行
        next_run = config.get_next_run_time()

        # 由于下次运行将超过结束时间,应该返回 None
        assert next_run is None

    def test_get_next_run_time_missing_interval(self):
        """测试缺少间隔参数。"""
        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.INTERVAL,
        )

        with pytest.raises(ValueError, match="interval_seconds required"):
            config.get_next_run_time()

    def test_get_next_run_time_missing_cron(self):
        """测试缺少 Cron 表达式。"""
        config = TaskConfig(
            name="test",
            schedule_type=ScheduleType.CRON,
        )

        with pytest.raises(ValueError, match="cron_expression required"):
            config.get_next_run_time()


class TestTask:
    """任务测试类。"""

    @pytest.mark.asyncio
    async def test_task_creation(self):
        """测试任务创建。"""

        async def sample_func():
            return "test"

        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        task = Task(func=sample_func, config=config)

        assert task.config.name == "test_task"
        assert task.status == TaskStatus.PENDING
        assert task.metrics.total_runs == 0

    @pytest.mark.asyncio
    async def test_task_execution_success(self):
        """测试任务成功执行。"""
        execution_count = {"count": 0}

        async def sample_func():
            execution_count["count"] += 1
            return "success"

        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        task = Task(func=sample_func, config=config)
        result = await task.execute()

        assert result == "success"
        assert execution_count["count"] == 1
        assert task.status == TaskStatus.COMPLETED
        assert task.metrics.total_runs == 1
        assert task.metrics.successful_runs == 1
        assert task.metrics.failed_runs == 0

    @pytest.mark.asyncio
    async def test_task_execution_failure(self):
        """测试任务执行失败。"""

        async def failing_func():
            raise ValueError("Test error")

        config = TaskConfig(
            name="failing_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            retry_policy=RetryPolicy.no_retry(),
        )

        task = Task(func=failing_func, config=config)

        with pytest.raises(ValueError, match="Test error"):
            await task.execute()

        assert task.status == TaskStatus.FAILED
        assert task.metrics.total_runs == 1
        assert task.metrics.successful_runs == 0
        assert task.metrics.failed_runs == 1

    @pytest.mark.asyncio
    async def test_task_execution_timeout(self):
        """测试任务执行超时。"""

        async def slow_func():
            await asyncio.sleep(5)
            return "done"

        config = TaskConfig(
            name="slow_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            timeout=0.1,  # 100ms 超时
            retry_policy=RetryPolicy.no_retry(),
        )

        task = Task(func=slow_func, config=config)

        with pytest.raises(asyncio.TimeoutError):
            await task.execute()

        assert task.status == TaskStatus.FAILED
        assert task.metrics.failed_runs == 1

    @pytest.mark.asyncio
    async def test_task_disabled(self):
        """测试禁用的任务。"""
        execution_count = {"count": 0}

        async def sample_func():
            execution_count["count"] += 1

        config = TaskConfig(
            name="disabled_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            enabled=False,
        )

        task = Task(func=sample_func, config=config)
        result = await task.execute()

        assert result is None
        assert execution_count["count"] == 0
        assert task.metrics.total_runs == 0

    @pytest.mark.asyncio
    async def test_task_max_instances(self):
        """测试最大并发实例限制。"""
        running = {"count": 0}
        max_concurrent = {"value": 0}

        async def concurrent_func():
            running["count"] += 1
            max_concurrent["value"] = max(max_concurrent["value"], running["count"])
            await asyncio.sleep(0.1)
            running["count"] -= 1

        config = TaskConfig(
            name="concurrent_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            max_instances=2,
        )

        task = Task(func=concurrent_func, config=config)

        # 启动 5 个并发执行
        results = await asyncio.gather(
            task.execute(),
            task.execute(),
            task.execute(),
            task.execute(),
            task.execute(),
        )

        # 应该有一些 None (被限制了),但具体数量可能因为并发时序而变化
        none_count = sum(1 for r in results if r is None)
        assert none_count > 0  # 至少有一些被限制
        assert max_concurrent["value"] <= 2  # 最大并发不超过 2

    @pytest.mark.asyncio
    async def test_task_cancel(self):
        """测试任务取消。"""

        async def sample_func():
            pass

        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        task = Task(func=sample_func, config=config)

        await task.cancel()

        assert task.status == TaskStatus.CANCELLED
        assert task.is_cancelled() is True

    def test_task_repr(self):
        """测试任务字符串表示。"""

        async def sample_func():
            pass

        config = TaskConfig(
            name="test_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
        )

        task = Task(func=sample_func, config=config)
        repr_str = repr(task)

        assert "Task" in repr_str
        assert "test_task" in repr_str
        assert "pending" in repr_str.lower() or "PENDING" in repr_str

    @pytest.mark.asyncio
    async def test_task_retry_status(self):
        """测试任务重试状态。"""
        attempt_count = {"value": 0}

        async def flaky_func():
            attempt_count["value"] += 1
            if attempt_count["value"] < 3:
                raise ValueError("Still failing")
            return "success"

        config = TaskConfig(
            name="flaky_task",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=10.0,
            retry_policy=RetryPolicy(
                max_attempts=5,
                initial_delay=0.01,  # 快速重试用于测试
                max_delay=0.1,
            ),
        )

        task = Task(func=flaky_func, config=config)
        result = await task.execute()

        assert result == "success"
        assert attempt_count["value"] == 3  # 失败2次后成功
        assert task.metrics.total_runs == 1
        assert task.metrics.successful_runs == 1
        # 状态应该最终是 COMPLETED,但在重试期间曾经是 RETRYING
