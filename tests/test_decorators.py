"""装饰器测试。"""

from datetime import datetime, timedelta

import pytest

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
    set_global_scheduler,
)
from chronflow.retry import RetryPolicy
from chronflow.task import ScheduleType


@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """在每个测试前后重置全局调度器状态。"""
    set_global_scheduler(None, clear_pending=True)
    yield
    set_global_scheduler(None, clear_pending=True)


class TestScheduledDecorator:
    """scheduled 装饰器测试类。"""

    def test_cron_decorator(self):
        """测试 cron 装饰器。"""

        @scheduled(cron="*/5 * * * * *")
        async def test_func():
            return "success"

        assert hasattr(test_func, "__chronflow_task__")
        task = test_func.__chronflow_task__

        assert task.config.name == "test_func"
        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "*/5 * * * * *"

    def test_interval_decorator(self):
        """测试 interval 装饰器。"""

        @scheduled(interval=30.0)
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.INTERVAL
        assert task.config.interval_seconds == 30.0

    def test_interval_with_timedelta(self):
        """测试使用 timedelta 的 interval 装饰器。"""

        @scheduled(interval=timedelta(minutes=5))
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.INTERVAL
        assert task.config.interval_seconds == 300.0

    def test_once_decorator(self):
        """测试 once 装饰器(通过 start_time)。"""
        start = datetime.now() + timedelta(hours=1)

        @scheduled(start_time=start)
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.ONCE
        assert task.config.start_time == start

    def test_custom_name(self):
        """测试自定义任务名称。"""

        @scheduled(interval=10, name="custom_task_name")
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.name == "custom_task_name"

    def test_with_retry_policy(self):
        """测试带重试策略的装饰器。"""
        retry = RetryPolicy(max_attempts=5)

        @scheduled(interval=10, retry_policy=retry)
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.retry_policy.max_attempts == 5

    def test_with_timeout(self):
        """测试带超时的装饰器。"""

        @scheduled(interval=10, timeout=30.0)
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.timeout == 30.0

    def test_with_max_instances(self):
        """测试带最大实例数的装饰器。"""

        @scheduled(interval=10, max_instances=5)
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.max_instances == 5

    def test_with_tags(self):
        """测试带标签的装饰器。"""

        @scheduled(interval=10, tags=["important", "daily"])
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert "important" in task.config.tags
        assert "daily" in task.config.tags

    def test_with_metadata(self):
        """测试带元数据的装饰器。"""

        @scheduled(interval=10, metadata={"author": "test", "version": "1.0"})
        async def test_func():
            return "success"

        task = test_func.__chronflow_task__

        assert task.config.metadata["author"] == "test"
        assert task.config.metadata["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_decorated_function_execution(self):
        """测试装饰后的函数仍可正常执行。"""
        executed = {"value": False}

        @scheduled(interval=10)
        async def test_func():
            executed["value"] = True
            return "success"

        result = await test_func()

        assert result == "success"
        assert executed["value"] is True


class TestCronDecorator:
    """cron 装饰器测试类。"""

    def test_basic_cron(self):
        """测试基本 cron 装饰器。"""

        @cron("0 0 * * * *")
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "0 0 * * * *"

    def test_cron_with_name(self):
        """测试带名称的 cron 装饰器。"""

        @cron("*/5 * * * * *", name="my_cron_task")
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.name == "my_cron_task"

    def test_cron_with_retry(self):
        """测试带重试的 cron 装饰器。"""

        @cron("0 0 * * * *", retry_policy=RetryPolicy.aggressive())
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.retry_policy.max_attempts == 10


class TestIntervalDecorator:
    """interval 装饰器测试类。"""

    def test_basic_interval(self):
        """测试基本 interval 装饰器。"""

        @interval(30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.INTERVAL
        assert task.config.interval_seconds == 30.0

    def test_interval_with_timedelta(self):
        """测试 timedelta interval 装饰器。"""

        @interval(timedelta(hours=2))
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.interval_seconds == 7200.0

    def test_interval_with_name(self):
        """测试带名称的 interval 装饰器。"""

        @interval(60, name="minute_task")
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.name == "minute_task"


class TestOnceDecorator:
    """once 装饰器测试类。"""

    def test_basic_once(self):
        """测试基本 once 装饰器。"""
        future_time = datetime.now() + timedelta(days=1)

        @once(at=future_time)
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.schedule_type == ScheduleType.ONCE
        assert task.config.start_time == future_time

    def test_once_with_name(self):
        """测试带名称的 once 装饰器。"""
        future_time = datetime.now() + timedelta(hours=1)

        @once(at=future_time, name="one_time_task")
        async def test_func():
            pass

        task = test_func.__chronflow_task__

        assert task.config.name == "one_time_task"


class TestEveryDecorator:
    """every 装饰器测试类。"""

    def test_every_seconds(self):
        """测试 every 秒间隔。"""

        @every(seconds=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.schedule_type == ScheduleType.INTERVAL
        assert task.config.interval_seconds == 30.0

    def test_every_minutes(self):
        """测试 every 分钟间隔。"""

        @every(minutes=5)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.interval_seconds == 300.0  # 5 * 60

    def test_every_hours(self):
        """测试 every 小时间隔。"""

        @every(hours=2)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.interval_seconds == 7200.0  # 2 * 3600

    def test_every_days(self):
        """测试 every 天间隔。"""

        @every(days=1)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.interval_seconds == 86400.0  # 1 * 86400

    def test_every_combined(self):
        """测试 every 组合间隔。"""

        @every(hours=1, minutes=30, seconds=45)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        expected = 1 * 3600 + 30 * 60 + 45
        assert task.config.interval_seconds == expected


class TestHourlyDecorator:
    """hourly 装饰器测试类。"""

    def test_hourly_default(self):
        """测试 hourly 默认（整点）。"""

        @hourly()
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "0 0 * * * *"

    def test_hourly_with_minute(self):
        """测试 hourly 指定分钟。"""

        @hourly(minute=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 30 * * * *"

    def test_hourly_with_all_params(self):
        """测试 hourly 所有参数。"""

        @hourly(minute=15)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 15 * * * *"


class TestDailyDecorator:
    """daily 装饰器测试类。"""

    def test_daily_default(self):
        """测试 daily 默认（午夜）。"""

        @daily()
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "0 0 0 * * *"

    def test_daily_with_hour(self):
        """测试 daily 指定小时。"""

        @daily(hour=9)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 0 9 * * *"

    def test_daily_with_hour_minute(self):
        """测试 daily 指定小时和分钟。"""

        @daily(hour=9, minute=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 30 9 * * *"

    def test_daily_with_multiple_params(self):
        """测试 daily 指定多个参数。"""

        @daily(hour=14, minute=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 30 14 * * *"


class TestWeeklyDecorator:
    """weekly 装饰器测试类。"""

    def test_weekly_default(self):
        """测试 weekly 默认（周日午夜）。"""

        @weekly()
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "0 0 0 * * 0"

    def test_weekly_with_day(self):
        """测试 weekly 指定星期几。"""

        @weekly(day=5)  # 星期五
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 0 0 * * 5"

    def test_weekly_with_time(self):
        """测试 weekly 指定时间。"""

        @weekly(day=3, hour=10, minute=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 30 10 * * 3"


class TestMonthlyDecorator:
    """monthly 装饰器测试类。"""

    def test_monthly_default(self):
        """测试 monthly 默认（1号午夜）。"""

        @monthly()
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.schedule_type == ScheduleType.CRON
        assert task.config.cron_expression == "0 0 0 1 * *"

    def test_monthly_with_day(self):
        """测试 monthly 指定日期。"""

        @monthly(day=15)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 0 0 15 * *"

    def test_monthly_with_time(self):
        """测试 monthly 指定时间。"""

        @monthly(day=1, hour=9, minute=30)
        async def test_func():
            pass

        task = test_func.__chronflow_task__
        assert task.config.cron_expression == "0 30 9 1 * *"
