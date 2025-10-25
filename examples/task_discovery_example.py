"""任务自动发现示例。

演示如何使用任务自动发现功能,快速集成项目中的定时任务。
"""

import asyncio
from pathlib import Path

from symphra_scheduler import Scheduler


async def main() -> None:
    """演示任务自动发现的多种用法。"""

    # 创建调度器
    scheduler = Scheduler()

    # ==========================================
    # 方法 1: 从目录自动发现任务
    # ==========================================

    # 假设项目结构如下:
    # my_app/
    # ├── modules/
    # │   ├── user/
    # │   │   └── task.py      # 用户相关任务
    # │   ├── email/
    # │   │   └── task.py      # 邮件相关任务
    # │   └── report/
    # │       └── task.py      # 报表相关任务

    # 扫描所有 task.py 文件并自动注册
    # tasks = scheduler.discover_tasks_from_directory("my_app/modules")
    # print(f"✓ 发现并注册了 {len(tasks)} 个任务")

    # ==========================================
    # 方法 2: 使用自定义文件名模式
    # ==========================================

    # 假设项目使用 *_tasks.py 命名约定:
    # my_app/
    # ├── user_tasks.py
    # ├── email_tasks.py
    # └── report_tasks.py

    # 扫描所有 *_tasks.py 文件
    # tasks = scheduler.discover_tasks_from_directory(
    #     "my_app",
    #     pattern="*_tasks.py",
    #     exclude_patterns=["test_*.py", "*_backup.py"]
    # )
    # print(f"✓ 发现并注册了 {len(tasks)} 个任务")

    # ==========================================
    # 方法 3: 从包中自动发现
    # ==========================================

    # 从已安装的包中扫描
    # tasks = scheduler.discover_tasks_from_package("my_app.tasks")
    # print(f"✓ 发现并注册了 {len(tasks)} 个任务")

    # ==========================================
    # 方法 4: 从指定模块列表导入
    # ==========================================

    # 精确指定要加载的模块
    # tasks = scheduler.discover_tasks_from_modules([
    #     "my_app.tasks.user_tasks",
    #     "my_app.tasks.email_tasks",
    # ])
    # print(f"✓ 发现并注册了 {len(tasks)} 个任务")

    # ==========================================
    # 演示: 创建示例任务目录结构
    # ==========================================

    # 创建示例目录
    example_dir = Path("example_tasks")
    example_dir.mkdir(exist_ok=True)

    # 创建示例任务文件
    task_file = example_dir / "task.py"
    task_file.write_text('''"""示例任务模块。"""

import asyncio
from symphra_scheduler import cron, interval


@interval(10)
async def example_interval_task():
    """每 10 秒执行一次。"""
    print("⏰ 示例间隔任务执行中...")


@cron("*/30 * * * * *")
async def example_cron_task():
    """每 30 秒执行一次。"""
    print("📅 示例 Cron 任务执行中...")
''')


    # 从示例目录发现任务
    tasks = scheduler.discover_tasks_from_directory(str(example_dir))
    for _task in tasks:
        pass

    # ==========================================
    # 查看已注册的所有任务
    # ==========================================
    task_list = scheduler.list_tasks()
    for _task_info in task_list:
        pass

    # ==========================================
    # 运行调度器(演示 10 秒)
    # ==========================================

    async def run_for_seconds(seconds: int) -> None:
        """运行调度器指定秒数。"""
        async with scheduler.run_context():
            await asyncio.sleep(seconds)

    await run_for_seconds(30)


    # 清理示例文件
    import shutil
    if example_dir.exists():
        shutil.rmtree(example_dir)


if __name__ == "__main__":
    asyncio.run(main())
