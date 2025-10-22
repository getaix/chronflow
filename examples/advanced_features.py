"""高级功能示例 - 展示新增的监控和便捷装饰器功能。"""

import asyncio

from chronflow import Scheduler, daily, every, hourly, weekly

# 创建调度器
scheduler = Scheduler()


# 使用新的便捷装饰器
@every(minutes=1)
async def every_minute():
    """每分钟执行一次。"""


@hourly(minute=30)
async def half_past_hour():
    """每小时的 30 分执行。"""


@daily(hour=9, minute=30)
async def morning_routine():
    """每天 9:30 执行。"""


@weekly(day=1, hour=10)
async def monday_meeting():
    """每周一 10:00 执行。"""


@every(seconds=30)
async def monitor_tasks():
    """监控任务状态 - 每 30 秒。"""
    # 获取任务列表
    tasks = scheduler.list_tasks()


    for task_info in tasks:
        if task_info['average_execution_time'] > 0:
            pass

    # 获取任务数量统计
    scheduler.get_task_count()




@every(seconds=15, tags=["demo", "test"])
async def tagged_task():
    """带标签的任务。"""


async def demonstrate_task_control():
    """演示任务控制功能。"""
    await asyncio.sleep(60)  # 等待 1 分钟

    await scheduler.pause_task("every_minute")

    await asyncio.sleep(30)

    await scheduler.resume_task("every_minute")

    # 根据标签获取任务
    scheduler.get_task_by_tag("demo")


async def main():
    """主函数。"""

    # 启动任务控制演示
    control_task = asyncio.create_task(demonstrate_task_control())

    try:
        # 启动调度器
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        control_task.cancel()
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
