"""SQLite 后端示例 - 演示使用 SQLite 本地持久化队列。

特点:
- 任务持久化到本地文件
- 重启后任务不丢失
- 无需外部服务
- 适合单机部署
"""

import asyncio

from chronflow import Scheduler, SchedulerConfig, interval
from chronflow.backends import SQLiteBackend

# 创建 SQLite 后端
sqlite_backend = SQLiteBackend(
    db_path="scheduler_demo.db",
    table_name="task_queue",
)

# 调度器配置
config = SchedulerConfig(
    max_workers=5,
    log_level="INFO",
)

scheduler = Scheduler(config=config, backend=sqlite_backend)


@interval(5)
async def persistent_task():
    """持久化任务 - 即使重启也会继续执行。"""


@interval(10)
async def check_database():
    """检查数据库状态。"""
    await sqlite_backend.get_queue_size()
    await sqlite_backend.health_check()



@interval(30)
async def cleanup_old_tasks():
    """定期清理旧任务记录。"""
    deleted = await sqlite_backend.cleanup_old_tasks(days=7)
    if deleted > 0:
        pass


async def main():
    """主函数。"""

    try:
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
