"""任务自动发现功能测试。"""


import pytest

from symphra_scheduler import Scheduler
from symphra_scheduler.discovery import TaskDiscovery


@pytest.fixture
def scheduler():
    """创建测试用的调度器实例。"""
    return Scheduler()


@pytest.fixture
def discovery(scheduler):
    """创建任务发现器实例。"""
    return TaskDiscovery(scheduler)


@pytest.fixture
def temp_task_dir(tmp_path):
    """创建临时任务目录。"""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    return task_dir


class TestTaskDiscovery:
    """测试任务发现器。"""

    def test_pattern_to_regex(self):
        """测试通配符模式转换为正则表达式。"""
        from symphra_scheduler.discovery import TaskDiscovery

        # 测试精确匹配
        pattern = TaskDiscovery._pattern_to_regex("task.py")
        assert pattern.match("task.py")
        assert not pattern.match("tasks.py")
        assert not pattern.match("my_task.py")

        # 测试通配符 *
        pattern = TaskDiscovery._pattern_to_regex("*_task.py")
        assert pattern.match("user_task.py")
        assert pattern.match("email_task.py")
        assert not pattern.match("task.py")

        # 测试前缀通配符
        pattern = TaskDiscovery._pattern_to_regex("task*.py")
        assert pattern.match("task.py")
        assert pattern.match("tasks.py")
        assert pattern.match("task_user.py")

        # 测试全匹配
        pattern = TaskDiscovery._pattern_to_regex("*.py")
        assert pattern.match("anything.py")
        assert pattern.match("test.py")
        assert not pattern.match("test.txt")

    def test_discover_from_directory_single_file(
        self, scheduler, temp_task_dir
    ):
        """测试从单个文件发现任务。"""
        # 创建任务文件
        task_file = temp_task_dir / "task.py"
        task_file.write_text('''
from symphra_scheduler import interval

@interval(10)
async def test_task():
    """测试任务。"""
    pass
''')

        # 发现任务
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="task.py"
        )

        assert len(tasks) == 1
        assert tasks[0].config.name == "test_task"

    def test_discover_from_directory_multiple_files(
        self, scheduler, temp_task_dir
    ):
        """测试从多个文件发现任务。"""
        # 创建多个任务文件
        (temp_task_dir / "user_tasks.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def user_task_1():
    pass

@interval(20)
async def user_task_2():
    pass
''')

        (temp_task_dir / "email_tasks.py").write_text('''
from symphra_scheduler import cron

@cron("*/5 * * * * *")
async def email_task():
    pass
''')

        # 发现任务
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="*_tasks.py"
        )

        assert len(tasks) == 3
        task_names = {t.config.name for t in tasks}
        assert task_names == {"user_task_1", "user_task_2", "email_task"}

    def test_discover_from_directory_recursive(
        self, scheduler, temp_task_dir
    ):
        """测试递归扫描子目录。"""
        # 创建子目录结构
        module1_dir = temp_task_dir / "module1"
        module1_dir.mkdir()
        (module1_dir / "task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def module1_task():
    pass
''')

        module2_dir = temp_task_dir / "module2"
        module2_dir.mkdir()
        (module2_dir / "task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def module2_task():
    pass
''')

        # 递归发现
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="task.py",
            recursive=True
        )

        assert len(tasks) == 2
        task_names = {t.config.name for t in tasks}
        assert task_names == {"module1_task", "module2_task"}

    def test_discover_from_directory_exclude_patterns(
        self, scheduler, temp_task_dir
    ):
        """测试排除模式。"""
        # 创建多个文件
        (temp_task_dir / "task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def production_task():
    pass
''')

        (temp_task_dir / "test_task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def test_task():
    pass
''')

        (temp_task_dir / "task_backup.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def backup_task():
    pass
''')

        # 排除测试和备份文件
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="*.py",
            exclude_patterns=["test_*.py", "*_backup.py"]
        )

        assert len(tasks) == 1
        assert tasks[0].config.name == "production_task"

    def test_discover_from_directory_nonexistent(self, scheduler):
        """测试扫描不存在的目录。"""
        with pytest.raises(ValueError, match="目录不存在"):
            scheduler.discover_tasks_from_directory("/nonexistent/path")

    def test_discover_from_directory_file_not_directory(
        self, scheduler, tmp_path
    ):
        """测试路径不是目录的情况。"""
        # 创建一个文件而非目录
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="路径不是目录"):
            scheduler.discover_tasks_from_directory(str(file_path))

    def test_discover_auto_register(self, scheduler, temp_task_dir):
        """测试自动注册功能。"""
        # 创建任务文件
        (temp_task_dir / "task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def auto_registered_task():
    pass
''')

        # 发现并自动注册
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="task.py"
        )

        # 验证任务已注册到调度器
        assert len(tasks) == 1
        assert "auto_registered_task" in scheduler._tasks
        assert scheduler.get_task("auto_registered_task") is not None

    def test_discover_multiple_decorators(self, scheduler, temp_task_dir):
        """测试发现多种装饰器定义的任务。"""
        (temp_task_dir / "task.py").write_text('''
from symphra_scheduler import interval, cron, daily, hourly
from datetime import datetime

@interval(10)
async def interval_task():
    pass

@cron("*/5 * * * * *")
async def cron_task():
    pass

@daily(hour=9)
async def daily_task():
    pass

@hourly(minute=30)
async def hourly_task():
    pass
''')

        tasks = scheduler.discover_tasks_from_directory(str(temp_task_dir))

        assert len(tasks) == 4
        task_names = {t.config.name for t in tasks}
        assert task_names == {
            "interval_task",
            "cron_task",
            "daily_task",
            "hourly_task",
        }

    def test_discover_handles_import_errors(
        self, scheduler, temp_task_dir, caplog
    ):
        """测试处理导入错误的模块。"""
        # 创建有语法错误的文件
        (temp_task_dir / "bad_task.py").write_text('''
from symphra_scheduler import interval

# 故意的语法错误
@interval(10
async def broken_task():
    pass
''')

        # 创建正常的文件
        (temp_task_dir / "good_task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def good_task():
    pass
''')

        # 应该跳过错误文件,继续处理正常文件
        tasks = scheduler.discover_tasks_from_directory(
            str(temp_task_dir),
            pattern="*_task.py"
        )

        # 应该只发现正常的任务
        assert len(tasks) == 1
        assert tasks[0].config.name == "good_task"

    def test_get_discovered_tasks(self, discovery, temp_task_dir):
        """测试获取已发现的任务列表。"""
        (temp_task_dir / "task.py").write_text('''
from symphra_scheduler import interval

@interval(10)
async def task1():
    pass

@interval(20)
async def task2():
    pass
''')

        # 发现任务
        discovery.discover_from_directory(str(temp_task_dir))

        # 获取已发现的任务
        discovered = discovery.get_discovered_tasks()
        assert len(discovered) == 2
        task_names = {t.config.name for t in discovered}
        assert task_names == {"task1", "task2"}


class TestSchedulerIntegration:
    """测试调度器集成。"""

    def test_scheduler_discover_methods_exist(self, scheduler):
        """测试调度器具有发现方法。"""
        assert hasattr(scheduler, "discover_tasks_from_directory")
        assert hasattr(scheduler, "discover_tasks_from_package")
        assert hasattr(scheduler, "discover_tasks_from_modules")

    def test_discovered_tasks_are_schedulable(
        self, scheduler, temp_task_dir
    ):
        """测试发现的任务可以被调度执行。"""
        executed = []

        (temp_task_dir / "task.py").write_text(f'''
from symphra_scheduler import interval

executed = {id(executed)}

@interval(1)
async def schedulable_task():
    import ctypes
    exec_list = ctypes.cast({id(executed)}, ctypes.py_object).value
    exec_list.append("executed")
''')

        # 发现任务
        tasks = scheduler.discover_tasks_from_directory(str(temp_task_dir))
        assert len(tasks) == 1

        # 任务应该已经注册到调度器
        task = scheduler.get_task("schedulable_task")
        assert task is not None
        assert task.config.enabled
