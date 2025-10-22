"""Redis 后端示例 - 演示如何使用 Redis 作为分布式队列后端。

运行前确保:
1. 已安装 Redis: pip install redis
2. Redis 服务正在运行: redis-server
"""

import asyncio

from chronflow import Scheduler, SchedulerConfig, cron, interval

try:
    from chronflow.backends import RedisBackend
except ImportError:
    exit(1)


# 配置 Redis 后端
redis_backend = RedisBackend(
    url="redis://localhost:6379/0",
    queue_name="chronflow:demo",
    max_connections=10,
)

# 调度器配置
config = SchedulerConfig(
    max_workers=20,  # 增加工作协程数
    queue_size=5000,
    log_level="INFO",
    timezone="Asia/Shanghai",
)

# 创建调度器
scheduler = Scheduler(config=config, backend=redis_backend)


@interval(3)
async def fast_task():
    """高频任务 - 每3秒执行。"""
    await asyncio.sleep(1)  # 模拟工作


@cron("0 * * * * *")  # 每分钟执行
async def minute_task():
    """每分钟任务。"""


@interval(10)
async def data_sync():
    """数据同步任务示例。"""
    await asyncio.sleep(2)  # 模拟同步操作


@interval(20)
async def health_check():
    """健康检查任务。"""
    await redis_backend.health_check()
    await redis_backend.get_queue_size()



async def main():
    """主函数。"""

    try:
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
