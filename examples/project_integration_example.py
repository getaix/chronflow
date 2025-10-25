"""实际项目集成示例。

演示如何在实际项目中使用任务自动发现功能。

项目结构示例:
my_project/
├── app/
│   ├── __init__.py
│   ├── main.py              # 主程序
│   ├── scheduler.py         # 调度器初始化
│   └── modules/
│       ├── __init__.py
│       ├── user/
│       │   ├── __init__.py
│       │   ├── task.py      # 用户模块定时任务
│       │   └── service.py
│       ├── email/
│       │   ├── __init__.py
│       │   ├── task.py      # 邮件模块定时任务
│       │   └── service.py
│       └── analytics/
│           ├── __init__.py
│           ├── task.py      # 分析模块定时任务
│           └── service.py
"""

import asyncio
from pathlib import Path

from symphra_scheduler import Scheduler, SchedulerConfig


def create_example_project_structure() -> Path:
    """创建示例项目结构。"""
    base_dir = Path("example_project")
    base_dir.mkdir(exist_ok=True)

    # 创建模块目录
    modules_dir = base_dir / "modules"
    modules_dir.mkdir(exist_ok=True)

    # 创建用户模块任务
    user_dir = modules_dir / "user"
    user_dir.mkdir(exist_ok=True)
    (user_dir / "__init__.py").write_text("")
    (user_dir / "task.py").write_text('''"""用户模块定时任务。"""

from symphra_scheduler import cron, daily, interval


@daily(hour=2, minute=0)
async def cleanup_inactive_users():
    """每天凌晨 2 点清理不活跃用户。"""
    print("🧹 正在清理不活跃用户...")
    # 模拟业务逻辑
    await asyncio.sleep(0.1)
    print("✓ 清理完成,已清理 42 个不活跃用户")


@cron("*/5 * * * * *")  # 每5秒执行一次
async def sync_user_profiles():
    """每 5 秒同步用户资料。"""
    print("🔄 正在同步用户资料...")
    await asyncio.sleep(0.1)
    print("✓ 同步完成,已更新 128 个用户资料")


@interval(3)  # 每3秒执行一次
async def check_user_status():
    """每 3 秒检查用户状态。"""
    print("👤 正在检查用户状态...")
    await asyncio.sleep(0.1)
    print("✓ 状态检查完成,在线用户: 256")


import asyncio
''')

    # 创建邮件模块任务
    email_dir = modules_dir / "email"
    email_dir.mkdir(exist_ok=True)
    (email_dir / "__init__.py").write_text("")
    (email_dir / "task.py").write_text('''"""邮件模块定时任务。"""

from symphra_scheduler import interval, every


@interval(4)  # 每4秒执行一次
async def send_pending_emails():
    """每 4 秒发送待发邮件。"""
    print("📧 正在发送待发邮件...")
    await asyncio.sleep(0.1)
    print("✓ 已发送 15 封邮件")


@every(seconds=7)  # 每7秒执行一次
async def cleanup_email_queue():
    """每 7 秒清理邮件队列。"""
    print("🗑️  正在清理邮件队列...")
    await asyncio.sleep(0.1)
    print("✓ 清理完成,删除了 23 条过期记录")


import asyncio
''')

    # 创建分析模块任务
    analytics_dir = modules_dir / "analytics"
    analytics_dir.mkdir(exist_ok=True)
    (analytics_dir / "__init__.py").write_text("")
    (analytics_dir / "task.py").write_text('''"""分析模块定时任务。"""

from symphra_scheduler import daily, weekly, cron


@cron("*/6 * * * * *")  # 每6秒执行一次
async def generate_realtime_analytics():
    """每 6 秒生成实时分析。"""
    print("📊 正在生成实时分析...")
    await asyncio.sleep(0.1)
    print("✓ 实时分析完成")


@daily(hour=0, minute=30)
async def generate_daily_report():
    """每天 00:30 生成日报。"""
    print("📊 正在生成每日报告...")
    await asyncio.sleep(0.1)
    print("✓ 日报生成完成")


@weekly(day=1, hour=9, minute=0)
async def generate_weekly_summary():
    """每周一 9:00 生成周报。"""
    print("📈 正在生成周报...")
    await asyncio.sleep(0.1)
    print("✓ 周报生成完成")


import asyncio
''')

    return base_dir


def cleanup_example_project(base_dir: Path) -> None:
    """清理示例项目。"""
    import shutil
    if base_dir.exists():
        shutil.rmtree(base_dir)


async def main() -> None:
    """主程序入口。"""


    # 创建示例项目结构
    project_dir = create_example_project_structure()

    # 初始化调度器
    config = SchedulerConfig(
        max_workers=10,
        enable_logging=True,
        log_level="INFO",
    )
    scheduler = Scheduler(config=config)

    # 自动发现并注册所有模块的任务
    scheduler.discover_tasks_from_directory(
        directory=str(project_dir / "modules"),
        pattern="task.py",
        recursive=True,
    )

    # 显示已注册的任务
    for task_info in scheduler.list_tasks():
        task_info['schedule_type']

    # 启动调度器并运行一段时间

    async def run_scheduler() -> None:
        """运行调度器。"""
        async with scheduler.run_context():
            await asyncio.sleep(20)

    await run_scheduler()

    # 显示统计信息
    for task_info in scheduler.list_tasks():
        task_info['name']
        task_info['total_runs']
        task_info['successful_runs']
        task_info['failed_runs']

    # 清理
    cleanup_example_project(project_dir)



if __name__ == "__main__":
    asyncio.run(main())
