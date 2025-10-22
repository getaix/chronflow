"""基于 Redis 的分布式调度队列后端。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

try:
    from redis.asyncio import Redis
except ImportError as err:
    raise ImportError(
        "Redis backend requires redis package. Install with: pip install redis"
    ) from err

from chronflow.backends.base import QueueBackend


class RedisBackend(QueueBackend):
    """适用于分布式系统的 Redis 队列实现。

    特性:
    - 分布式任务队列
    - 重启后的持久化能力
    - 借助 Redis 的高性能
    - 支持多工作协程并发

    安装: pip install redis
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        queue_name: str = "chronflow:queue",
        pending_set: str = "chronflow:pending",
        max_connections: int = 10,
    ) -> None:
        """初始化 Redis 后端。

        Args:
            url: Redis 连接 URL
            queue_name: Redis 有序集合的队列名称
            pending_set: Redis 集合用于记录待处理任务的名称
            max_connections: 最大 Redis 连接数
        """
        self.url = url
        self.queue_name = queue_name
        self.pending_set = pending_set
        self.max_connections = max_connections
        self._redis: Redis | None = None

    async def connect(self) -> None:
        """连接到 Redis。"""
        self._redis = Redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=self.max_connections,
        )
        # 测试连接
        await self._redis.ping()

    async def disconnect(self) -> None:
        """断开与 Redis 的连接。"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def enqueue(
        self,
        task_id: str,
        task_name: str,
        scheduled_time: datetime,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """将任务加入 Redis 有序集合。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        task_data = {
            "task_id": task_id,
            "task_name": task_name,
            "scheduled_time": scheduled_time.isoformat(),
            "payload": payload,
            "priority": priority,
        }

        # 使用时间戳作为分数实现基于时间的调度
        # 根据优先级调整分数(优先级越高=越早执行)
        score = scheduled_time.timestamp() - (priority * 1000)

        await self._redis.zadd(
            self.queue_name,
            {json.dumps(task_data): score},
        )

    async def dequeue(self, limit: int = 1) -> list[dict[str, Any]]:
        """从 Redis 获取就绪任务。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        now = datetime.now().timestamp()

        # 获取当前时间之前调度的任务
        tasks = await self._redis.zrangebyscore(
            self.queue_name,
            min="-inf",
            max=now,
            start=0,
            num=limit,
        )

        ready_tasks = []
        for task_json in tasks:
            task_data = json.loads(task_json)
            task_id = task_data["task_id"]

            # 原子性地移动到待处理集合
            pipe = self._redis.pipeline()
            pipe.zrem(self.queue_name, task_json)
            pipe.sadd(self.pending_set, task_id)
            await pipe.execute()

            ready_tasks.append(task_data)

        return ready_tasks

    async def acknowledge(self, task_id: str) -> None:
        """从待处理集合移除任务。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        await self._redis.srem(self.pending_set, task_id)

    async def reject(self, task_id: str, requeue: bool = False) -> None:
        """处理失败任务。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        await self._redis.srem(self.pending_set, task_id)

        if requeue:
            # 可以在此处实现重新入队逻辑
            pass

    async def get_queue_size(self) -> int:
        """获取队列中的任务总数。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        queue_size = await self._redis.zcard(self.queue_name)
        pending_size = await self._redis.scard(self.pending_set)

        return queue_size + pending_size

    async def clear(self) -> None:
        """清空所有任务。"""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        pipe = self._redis.pipeline()
        pipe.delete(self.queue_name)
        pipe.delete(self.pending_set)
        await pipe.execute()

    async def health_check(self) -> bool:
        """检查 Redis 的健康状态。"""
        if not self._redis:
            return False

        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        """字符串表示。"""
        return f"RedisBackend(url={self.url}, queue={self.queue_name})"
