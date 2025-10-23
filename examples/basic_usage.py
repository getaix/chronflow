"""基础使用示例 - 演示最简单的定时任务用法。"""

import asyncio
import datetime
import logging
import time

from chronflow import Scheduler, cron, interval

# 创建调度器实例
scheduler = Scheduler()

logger = logging.getLogger(__name__)

@interval(1)  # 每1秒执行一次
async def hello_world():
    """简单的间隔任务示例。"""
    print("hello world")
    # logger.info(f"hello world, {datetime.time()}")


@cron("*/10 * * * * *")  # 每10秒执行
async def cron_task():
    """Cron 表达式任务示例。"""


@interval(15)
async def show_stats():
    """显示调度器统计信息。"""
    await scheduler.get_stats()


async def main():
    """主函数。"""
    daemon = True
    try:
        # 启动调度器(守护模式)
        await scheduler.start(daemon=daemon)
    except asyncio.CancelledError:
        await scheduler.stop(daemon=daemon)
    except KeyboardInterrupt:
        await scheduler.stop(daemon=daemon)


if __name__ == "__main__":
    try:
        asyncio.run(main())
        # asyncio.run(scheduler.stop_daemon())
    except KeyboardInterrupt:
        logger.info("检测到中断信号，调度器已停止。")
        asyncio.run(scheduler.stop(daemon=True))
