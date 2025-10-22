"""基础使用示例 - 演示最简单的定时任务用法。"""

import asyncio

from fscheduler import Scheduler, cron, interval

# 创建调度器实例
scheduler = Scheduler()


@interval(5)  # 每5秒执行一次
async def hello_world():
    """简单的间隔任务示例。"""


@cron("*/10 * * * * *")  # 每10秒执行
async def cron_task():
    """Cron 表达式任务示例。"""


@interval(15)
async def show_stats():
    """显示调度器统计信息。"""
    await scheduler.get_stats()


async def main():
    """主函数。"""

    try:
        # 启动调度器(守护模式)
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
