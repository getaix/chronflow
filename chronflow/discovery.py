"""任务自动发现和加载机制。

该模块提供了按约定自动发现并注册定时任务的功能,简化项目集成流程。

特性:
- 支持按目录路径扫描 Python 模块
- 支持按包名递归扫描
- 支持自定义文件名模式匹配
- 自动发现装饰器定义的任务
- 灵活的过滤和排除规则
- 线程安全的任务注册
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chronflow.scheduler import Scheduler
    from chronflow.task import Task


class TaskDiscovery:
    """任务自动发现和加载器。

    用于自动扫描目录或包,发现并注册使用装饰器定义的任务。

    示例:
        # 扫描目录下所有 task.py 文件
        discovery = TaskDiscovery(scheduler)
        discovery.discover_from_directory("my_app/modules")

        # 扫描包下所有 *_tasks.py 文件
        discovery.discover_from_package("my_app.tasks", pattern="*_tasks.py")

        # 排除特定模块
        discovery.discover_from_directory(
            "my_app",
            exclude_patterns=["test_*", "*_backup.py"]
        )
    """

    def __init__(self, scheduler: Scheduler) -> None:
        """初始化任务发现器。

        参数:
            scheduler: 调度器实例,用于注册发现的任务
        """
        self.scheduler = scheduler
        self._discovered_tasks: list[Task] = []

    def discover_from_directory(
        self,
        directory: str | Path,
        *,
        pattern: str = "task.py",
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
        auto_register: bool = True,
    ) -> list[Task]:
        """从目录中发现任务。

        参数:
            directory: 要扫描的目录路径
            pattern: 文件名匹配模式,支持通配符 (默认: "task.py")
            recursive: 是否递归扫描子目录 (默认: True)
            exclude_patterns: 排除的文件名模式列表
            auto_register: 是否自动注册发现的任务 (默认: True)

        返回值:
            发现的任务列表

        示例:
            # 扫描所有 task.py
            tasks = discovery.discover_from_directory("my_app/modules")

            # 扫描所有 *_task.py 和 *_tasks.py
            tasks = discovery.discover_from_directory(
                "my_app",
                pattern="*task*.py",
                exclude_patterns=["test_*.py"]
            )
        """
        directory_path = Path(directory).resolve()

        if not directory_path.exists():
            raise ValueError(f"目录不存在: {directory}")

        if not directory_path.is_dir():
            raise ValueError(f"路径不是目录: {directory}")

        # 转换通配符模式为正则表达式
        pattern_regex = self._pattern_to_regex(pattern)
        exclude_regexes = [
            self._pattern_to_regex(p) for p in (exclude_patterns or [])
        ]

        discovered_tasks: list[Task] = []

        # 扫描目录
        if recursive:
            python_files = directory_path.rglob("*.py")
        else:
            python_files = directory_path.glob("*.py")

        for file_path in python_files:
            # 跳过 __pycache__ 和隐藏文件
            if "__pycache__" in file_path.parts or file_path.name.startswith("."):
                continue

            # 检查是否匹配模式
            if not pattern_regex.match(file_path.name):
                continue

            # 检查是否被排除
            if any(regex.match(file_path.name) for regex in exclude_regexes):
                continue

            # 尝试导入并发现任务
            try:
                tasks = self._load_tasks_from_file(file_path)
                discovered_tasks.extend(tasks)
            except Exception as e:
                # 记录警告但继续扫描其他文件
                self.scheduler._log.warning(
                    "导入模块失败,跳过",
                    file=str(file_path),
                    error=str(e),
                )

        # 自动注册任务
        if auto_register:
            for task in discovered_tasks:
                self._register_task(task)

        self._discovered_tasks.extend(discovered_tasks)
        return discovered_tasks

    def discover_from_package(
        self,
        package_name: str,
        *,
        pattern: str = "task.py",
        exclude_patterns: list[str] | None = None,
        auto_register: bool = True,
    ) -> list[Task]:
        """从包中发现任务。

        参数:
            package_name: 包名 (例如: "my_app.tasks")
            pattern: 文件名匹配模式
            exclude_patterns: 排除的文件名模式列表
            auto_register: 是否自动注册发现的任务

        返回值:
            发现的任务列表

        示例:
            # 扫描包及其子包
            tasks = discovery.discover_from_package("my_app.tasks")

            # 扫描特定模式
            tasks = discovery.discover_from_package(
                "my_app",
                pattern="*_tasks.py"
            )
        """
        try:
            # 导入包并获取其路径
            package = importlib.import_module(package_name)
            if not hasattr(package, "__path__"):
                raise ValueError(f"{package_name} 不是一个包")

            # 获取包的目录路径
            package_path = Path(package.__path__[0])

            # 使用目录扫描方法
            return self.discover_from_directory(
                package_path,
                pattern=pattern,
                recursive=True,
                exclude_patterns=exclude_patterns,
                auto_register=auto_register,
            )

        except ImportError as e:
            raise ValueError(f"无法导入包 {package_name}: {e}") from e

    def discover_from_modules(
        self,
        module_names: list[str],
        *,
        auto_register: bool = True,
    ) -> list[Task]:
        """从指定的模块列表中发现任务。

        参数:
            module_names: 模块名列表 (例如: ["app.tasks.user", "app.tasks.email"])
            auto_register: 是否自动注册发现的任务

        返回值:
            发现的任务列表

        示例:
            tasks = discovery.discover_from_modules([
                "my_app.tasks.user_tasks",
                "my_app.tasks.email_tasks",
            ])
        """
        discovered_tasks: list[Task] = []

        for module_name in module_names:
            try:
                # 导入模块
                importlib.import_module(module_name)

                # 从全局调度器的待注册列表中获取任务
                # 注意: 导入时装饰器会自动将任务添加到全局调度器
                # 这里我们直接从调度器的已注册任务中获取
                # (因为构造函数中 use_global_scheduler=True)

            except ImportError as e:
                self.scheduler._log.warning(
                    "导入模块失败,跳过",
                    module=module_name,
                    error=str(e),
                )

        # 由于装饰器已自动注册,我们从调度器获取当前任务列表
        current_tasks = list(self.scheduler._tasks.values())
        discovered_tasks = current_tasks

        self._discovered_tasks.extend(discovered_tasks)
        return discovered_tasks

    def get_discovered_tasks(self) -> list[Task]:
        """获取所有已发现的任务。

        返回值:
            已发现的任务列表
        """
        return self._discovered_tasks.copy()

    def _load_tasks_from_file(self, file_path: Path) -> list[Task]:
        """从 Python 文件中加载任务。

        参数:
            file_path: Python 文件路径

        返回值:
            文件中发现的任务列表
        """
        # 生成模块名
        module_name = self._file_path_to_module_name(file_path)

        # 记录导入前的任务数量
        tasks_before = set(self.scheduler._tasks.keys())

        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 记录导入后的任务数量,计算新增任务
        tasks_after = set(self.scheduler._tasks.keys())
        new_task_names = tasks_after - tasks_before

        # 获取新增的任务实例
        new_tasks = [
            self.scheduler._tasks[name] for name in new_task_names
        ]

        self.scheduler._log.debug(
            "从文件加载任务",
            file=str(file_path),
            task_count=len(new_tasks),
            task_names=[t.config.name for t in new_tasks],
        )

        return new_tasks

    def _register_task(self, task: Task) -> None:
        """注册任务到调度器。

        参数:
            task: 要注册的任务
        """
        try:
            # 尝试注册任务
            # 注意: 由于装饰器已经自动注册过,这里可能会遇到重复
            # 我们可以选择跳过或者更新
            if task.config.name not in self.scheduler._tasks:
                self.scheduler.register_task(task)
        except ValueError:
            # 任务已存在,跳过
            pass

    @staticmethod
    def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
        """将通配符模式转换为正则表达式。

        参数:
            pattern: 通配符模式 (例如: "*.py", "task_*.py")

        返回值:
            编译后的正则表达式
        """
        # 转义特殊字符
        regex_pattern = re.escape(pattern)

        # 替换通配符
        regex_pattern = regex_pattern.replace(r"\*", ".*")
        regex_pattern = regex_pattern.replace(r"\?", ".")

        # 确保完整匹配
        regex_pattern = f"^{regex_pattern}$"

        return re.compile(regex_pattern)

    @staticmethod
    def _file_path_to_module_name(file_path: Path) -> str:
        """将文件路径转换为模块名。

        参数:
            file_path: Python 文件路径

        返回值:
            模块名
        """
        # 移除 .py 后缀
        parts = file_path.with_suffix("").parts

        # 将路径组件连接为模块名
        # 注意: 这是一个简化版本,实际项目中可能需要更复杂的逻辑
        module_name = ".".join(parts[-3:])  # 取最后3个部分避免路径过长

        return module_name
