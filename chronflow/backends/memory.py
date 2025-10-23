"""默认的内存队列后端,无需外部依赖。"""

from __future__ import annotations

import asyncio
import heapq
from datetime import datetime, timezone
from typing import Any

from chronflow.backends.base import QueueBackend


class MemoryBackend(QueueBackend):
    """基于 heapq 的内存优先队列实现。

    特点:
    - 默认后端,无需任何外部依赖
    - 适用于单进程应用和测试场景
    """

    def __init__(self, max_size: int = 10000) -> None:
        """初始化内存后端。

        Args:
            max_size: 队列允许的最大任务数量
        """
        self.max_size = max_size
        self._queue: list[tuple[datetime, int, str, dict[str, Any]]] = []
        self._lock = asyncio.Lock()
        self._pending: set[str] = set()
        self._counter = 0  # 确保优先级相同的任务稳定排序

    async def connect(self) -> None:
        """内存后端无需建立连接。"""
        pass

    async def disconnect(self) -> None:
        """内存后端无需显式断开连接。"""
        self._queue.clear()
        self._pending.clear()

    async def enqueue(
        self,
        task_id: str,
        task_name: str,
        scheduled_time: datetime,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """将任务加入优先队列。"""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise RuntimeError(f"Queue is full (max_size={self.max_size})")

            # 使用负优先级实现最大堆行为
            # 包含计数器以实现相同优先级的稳定排序(FIFO)
            task_data = {
                "task_id": task_id,
                "task_name": task_name,
                "scheduled_time": scheduled_time.isoformat(),
                "payload": payload,
                "priority": priority,
            }

            heapq.heappush(
                self._queue,
                (scheduled_time, -priority, self._counter, task_id, task_data),
            )
            self._counter += 1

    async def dequeue(self, limit: int = 1) -> list[dict[str, Any]]:
        """从队列中获取已就绪的任务。"""
        async with self._lock:
            now = datetime.now(timezone.utc)
            ready_tasks: list[dict[str, Any]] = []

            # 查看任务并收集就绪的任务
            temp_tasks = []
            while self._queue and len(ready_tasks) < limit:
                scheduled_time, neg_priority, counter, task_id, task_data = heapq.heappop(
                    self._queue
                )

                if scheduled_time <= now and task_id not in self._pending:
                    ready_tasks.append(task_data)
                    self._pending.add(task_id)
                else:
                    # 如果未就绪则放回队列
                    temp_tasks.append((scheduled_time, neg_priority, counter, task_id, task_data))

            # 将未就绪的任务放回队列
            for task in temp_tasks:
                heapq.heappush(self._queue, task)

            return ready_tasks

    async def acknowledge(self, task_id: str) -> None:
        """将任务从待处理集合中移除。"""
        async with self._lock:
            self._pending.discard(task_id)

    async def reject(self, task_id: str, requeue: bool = False) -> None:
        """处理失败任务。"""
        async with self._lock:
            self._pending.discard(task_id)

            if requeue:
                # 查找并重新入队任务
                # 在实际实现中,你需要跟踪被拒绝的任务
                pass

    async def get_queue_size(self) -> int:
        """获取队列中的任务总数。"""
        async with self._lock:
            return len(self._queue) + len(self._pending)

    async def clear(self) -> None:
        """清除所有任务。"""
        async with self._lock:
            self._queue.clear()
            self._pending.clear()
            self._counter = 0

    async def health_check(self) -> bool:
        """内存后端始终处于健康状态。"""
        return True

    def __repr__(self) -> str:
        """返回可读的信息。"""
        return f"MemoryBackend(queue_size={len(self._queue)}, pending={len(self._pending)})"
