"""测试装饰器的高级功能和边界情况。"""
import pytest

from chronflow import (
    Scheduler,
    daily,
    every,
    hourly,
    interval,
    monthly,
    weekly,
)
from chronflow.decorators import _pending_tasks, set_global_scheduler


class TestDecoratorErrorHandling:
    """测试装饰器的错误处理"""

    def teardown_method(self):
        """每个测试后清理全局调度器"""
        set_global_scheduler(None, clear_pending=True)

    def test_every_decorator_no_time_unit_raises_error(self):
        """测试 every 装饰器未指定时间单位时抛出错误"""
        with pytest.raises(ValueError, match="必须指定至少一个时间单位"):

            @every()
            async def test_func():
                pass

    def test_hourly_decorator_invalid_minute_raises_error(self):
        """测试 hourly 装饰器分钟参数超出范围"""
        with pytest.raises(ValueError, match="minute 必须在 0-59 之间"):

            @hourly(minute=60)
            async def test_func():
                pass

        with pytest.raises(ValueError, match="minute 必须在 0-59 之间"):

            @hourly(minute=-1)
            async def test_func():
                pass

    def test_daily_decorator_invalid_hour_raises_error(self):
        """测试 daily 装饰器小时参数超出范围"""
        with pytest.raises(ValueError, match="hour 必须在 0-23 之间"):

            @daily(hour=24)
            async def test_func():
                pass

        with pytest.raises(ValueError, match="hour 必须在 0-23 之间"):

            @daily(hour=-1)
            async def test_func():
                pass

    def test_daily_decorator_invalid_minute_raises_error(self):
        """测试 daily 装饰器分钟参数超出范围"""
        with pytest.raises(ValueError, match="minute 必须在 0-59 之间"):

            @daily(hour=10, minute=60)
            async def test_func():
                pass

    def test_weekly_decorator_invalid_day_raises_error(self):
        """测试 weekly 装饰器星期参数超出范围"""
        with pytest.raises(
            ValueError, match="day 必须在 0-6 之间 \\(0=周日, 1=周一, ..., 6=周六\\)"
        ):

            @weekly(day=7)
            async def test_func():
                pass

        with pytest.raises(
            ValueError, match="day 必须在 0-6 之间 \\(0=周日, 1=周一, ..., 6=周六\\)"
        ):

            @weekly(day=-1)
            async def test_func():
                pass

    def test_weekly_decorator_invalid_hour_raises_error(self):
        """测试 weekly 装饰器小时参数超出范围"""
        with pytest.raises(ValueError, match="hour 必须在 0-23 之间"):

            @weekly(day=1, hour=24)
            async def test_func():
                pass

    def test_weekly_decorator_invalid_minute_raises_error(self):
        """测试 weekly 装饰器分钟参数超出范围"""
        with pytest.raises(ValueError, match="minute 必须在 0-59 之间"):

            @weekly(day=1, hour=10, minute=60)
            async def test_func():
                pass

    def test_monthly_decorator_invalid_day_raises_error(self):
        """测试 monthly 装饰器日期参数超出范围"""
        with pytest.raises(ValueError, match="day 必须在 1-31 之间"):

            @monthly(day=0)
            async def test_func():
                pass

        with pytest.raises(ValueError, match="day 必须在 1-31 之间"):

            @monthly(day=32)
            async def test_func():
                pass

    def test_monthly_decorator_invalid_hour_raises_error(self):
        """测试 monthly 装饰器小时参数超出范围"""
        with pytest.raises(ValueError, match="hour 必须在 0-23 之间"):

            @monthly(day=15, hour=24)
            async def test_func():
                pass

    def test_monthly_decorator_invalid_minute_raises_error(self):
        """测试 monthly 装饰器分钟参数超出范围"""
        with pytest.raises(ValueError, match="minute 必须在 0-59 之间"):

            @monthly(day=15, hour=10, minute=60)
            async def test_func():
                pass


class TestDecoratorPendingTasks:
    """测试装饰器的待注册任务功能"""

    def teardown_method(self):
        """每个测试后清理全局调度器"""
        set_global_scheduler(None, clear_pending=True)

    def test_pending_tasks_registered_when_scheduler_set(self):
        """测试设置调度器时注册待注册任务"""
        # 在没有全局调度器时定义任务
        @interval(seconds=1, name="pending_task")
        async def test_func():
            pass

        # 任务应该在待注册列表中
        assert any(t.config.name == "pending_task" for t in _pending_tasks)

        # 创建并设置全局调度器
        scheduler = Scheduler()
        set_global_scheduler(scheduler)

        # 待注册任务应该已被注册
        assert scheduler.get_task("pending_task") is not None

        # 待注册列表应该被清空
        assert len(_pending_tasks) == 0

    def test_duplicate_pending_task_not_added(self):
        """测试重复的待注册任务不会被添加"""
        # 清空待注册列表
        _pending_tasks.clear()

        # 定义相同名称的任务两次
        @interval(seconds=1, name="duplicate_task")
        async def test_func1():
            pass

        @interval(seconds=1, name="duplicate_task")
        async def test_func2():
            pass

        # 待注册列表中应该只有一个任务
        duplicate_count = sum(
            1 for t in _pending_tasks if t.config.name == "duplicate_task"
        )
        assert duplicate_count == 1

    def test_clear_pending_tasks_on_scheduler_clear(self):
        """测试清除调度器时清空待注册任务"""
        # 定义任务
        @interval(seconds=1, name="clear_test_task")
        async def test_func():
            pass

        assert len(_pending_tasks) > 0

        # 清除调度器并清空待注册任务
        set_global_scheduler(None, clear_pending=True)

        # 待注册列表应该被清空
        assert len(_pending_tasks) == 0


class TestDecoratorSchedulerIntegration:
    """测试装饰器与调度器的集成"""

    def teardown_method(self):
        """每个测试后清理全局调度器"""
        set_global_scheduler(None, clear_pending=True)

    def test_decorator_with_existing_scheduler(self):
        """测试在已有全局调度器时使用装饰器"""
        # 先创建调度器
        scheduler = Scheduler()
        set_global_scheduler(scheduler)

        # 然后定义任务
        @interval(seconds=1, name="immediate_register_task")
        async def test_func():
            pass

        # 任务应该立即被注册
        assert scheduler.get_task("immediate_register_task") is not None

        # 待注册列表应该是空的
        assert not any(
            t.config.name == "immediate_register_task" for t in _pending_tasks
        )

    def test_decorator_duplicate_name_with_scheduler(self):
        """测试在调度器中注册重复名称的任务"""
        scheduler = Scheduler()
        set_global_scheduler(scheduler)

        # 定义第一个任务
        @interval(seconds=1, name="duplicate_name")
        async def test_func1():
            pass

        # 定义同名任务(应该被跳过)
        @interval(seconds=1, name="duplicate_name")
        async def test_func2():
            pass

        # 调度器中应该只有一个任务
        task_count = sum(1 for t in scheduler.list_tasks() if t["name"] == "duplicate_name")
        assert task_count == 1

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


class TestDecoratorCombinations:
    """测试装饰器的各种组合"""

    def teardown_method(self):
        """每个测试后清理全局调度器"""
        set_global_scheduler(None, clear_pending=True)

    def test_every_with_multiple_units(self):
        """测试 every 装饰器同时使用多个时间单位"""

        @every(hours=1, minutes=30, seconds=45)
        async def test_func():
            pass

        # 总秒数应该是 1*3600 + 30*60 + 45 = 5445
        task = test_func.__chronflow_task__
        assert task.config.interval_seconds == 5445

    def test_every_with_days(self):
        """测试 every 装饰器使用天数"""

        @every(days=2)
        async def test_func():
            pass

        # 总秒数应该是 2*86400 = 172800
        task = test_func.__chronflow_task__
        assert task.config.interval_seconds == 172800

    def test_hourly_various_minutes(self):
        """测试 hourly 装饰器的各种分钟值"""
        for minute in [0, 15, 30, 45, 59]:

            @hourly(minute=minute, name=f"hourly_{minute}")
            async def test_func():
                pass

            task = test_func.__chronflow_task__
            # 验证 cron 表达式
            assert task.config.cron_expression == f"0 {minute} * * * *"

    def test_daily_various_times(self):
        """测试 daily 装饰器的各种时间值"""
        test_cases = [(0, 0), (9, 30), (12, 0), (23, 59)]

        for hour, minute in test_cases:

            @daily(hour=hour, minute=minute, name=f"daily_{hour}_{minute}")
            async def test_func():
                pass

            task = test_func.__chronflow_task__
            assert task.config.cron_expression == f"0 {minute} {hour} * * *"

    def test_weekly_all_days(self):
        """测试 weekly 装饰器的所有星期"""
        for day in range(7):

            @weekly(day=day, hour=10, minute=0, name=f"weekly_{day}")
            async def test_func():
                pass

            task = test_func.__chronflow_task__
            assert task.config.cron_expression == f"0 0 10 * * {day}"

    def test_monthly_various_days(self):
        """测试 monthly 装饰器的各种日期"""
        for day in [1, 15, 28, 31]:

            @monthly(day=day, hour=0, minute=0, name=f"monthly_{day}")
            async def test_func():
                pass

            task = test_func.__chronflow_task__
            assert task.config.cron_expression == f"0 0 0 {day} * *"
