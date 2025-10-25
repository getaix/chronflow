"""队列后端的基础接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class QueueBackend(ABC):
    """队列后端的抽象基类。"""

    @abstractmethod
    async def connect(self) -> None:
        """建立与后端的连接。"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """关闭与后端的连接。"""
        pass

    @abstractmethod
    async def enqueue(
        self,
        task_id: str,
        task_name: str,
        scheduled_time: datetime,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """将任务加入队列。

        Args:
            task_id: 任务的唯一标识
            task_name: 任务名称
            scheduled_time: 任务计划执行时间
            payload: 任务数据和参数
            priority: 任务优先级(数值越大越优先)
        """
        pass

    @abstractmethod
    async def dequeue(self, limit: int = 1) -> list[dict[str, Any]]:
        """从队列中获取就绪任务。

        Args:
            limit: 最多获取的任务数量

        Returns:
            已准备执行的任务负载列表
        """
        pass

    @abstractmethod
    async def acknowledge(self, task_id: str) -> None:
        """标记任务成功完成。

        Args:
            task_id: 已完成任务的标识
        """
        pass

    @abstractmethod
    async def reject(self, task_id: str, requeue: bool = False) -> None:
        """标记任务执行失败。

        Args:
            task_id: 失败任务的标识
            requeue: 是否将任务重新入队
        """
        pass

    @abstractmethod
    async def get_queue_size(self) -> int:
        """获取队列中的待处理任务数量。"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """清空队列中的所有任务。"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """检查后端是否健康且可访问。"""
        pass
