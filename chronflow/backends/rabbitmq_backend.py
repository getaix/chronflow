"""基于 RabbitMQ 的队列后端,提供高可靠性消息队列支持。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

try:
    from aio_pika import Message, connect_robust
    from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue
except ImportError as err:
    raise ImportError("RabbitMQ 后端需要 aio-pika 包。安装方式: pip install aio-pika") from err

from chronflow.backends.base import QueueBackend


class RabbitMQBackend(QueueBackend):
    """基于 RabbitMQ 的队列实现,适用于高可靠性分布式系统。

    特性:
    - 消息持久化,防止数据丢失
    - 支持多个消费者并发处理
    - 自动重连机制
    - 延迟消息支持(需要 rabbitmq_delayed_message_exchange 插件)

    安装: pip install aio-pika
    """

    def __init__(
        self,
        url: str = "amqp://guest:guest@localhost:5672/",
        queue_name: str = "chronflow_tasks",
        durable: bool = True,
        prefetch_count: int = 10,
    ) -> None:
        """初始化 RabbitMQ 后端。

        Args:
            url: RabbitMQ 连接 URL
            queue_name: 队列名称
            durable: 是否持久化队列
            prefetch_count: 预取消息数量
        """
        self.url = url
        self.queue_name = queue_name
        self.durable = durable
        self.prefetch_count = prefetch_count

        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queue: AbstractQueue | None = None
        self._pending_tags: dict[str, int] = {}

    async def connect(self) -> None:
        """连接到 RabbitMQ。"""
        self._connection = await connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self.prefetch_count)

        # 声明队列
        self._queue = await self._channel.declare_queue(
            self.queue_name,
            durable=self.durable,
            arguments={
                "x-message-ttl": 86400000,  # 24小时 TTL
            },
        )

    async def disconnect(self) -> None:
        """断开 RabbitMQ 连接。"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._queue = None

    async def enqueue(
        self,
        task_id: str,
        task_name: str,
        scheduled_time: datetime,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """将任务添加到 RabbitMQ 队列。"""
        if not self._channel:
            raise RuntimeError("RabbitMQ 未连接")

        task_data = {
            "task_id": task_id,
            "task_name": task_name,
            "scheduled_time": scheduled_time.isoformat(),
            "payload": payload,
            "priority": priority,
        }

        # 计算延迟时间(毫秒)
        delay_ms = max(0, int((scheduled_time - datetime.now()).total_seconds() * 1000))

        message = Message(
            body=json.dumps(task_data).encode(),
            priority=priority,
            delivery_mode=2,  # 持久化消息
            headers={"x-delay": delay_ms} if delay_ms > 0 else None,
        )

        await self._channel.default_exchange.publish(
            message,
            routing_key=self.queue_name,
        )

    async def dequeue(self, limit: int = 1) -> list[dict[str, Any]]:
        """从 RabbitMQ 获取就绪的任务。"""
        if not self._queue:
            raise RuntimeError("RabbitMQ 未连接")

        ready_tasks = []

        for _ in range(limit):
            message = await self._queue.get(timeout=0.1, fail=False)
            if message is None:
                break

            task_data = json.loads(message.body.decode())
            task_id = task_data["task_id"]

            # 保存 delivery_tag 用于后续 ack/reject
            self._pending_tags[task_id] = message.delivery_tag

            ready_tasks.append(task_data)

        return ready_tasks

    async def acknowledge(self, task_id: str) -> None:
        """确认任务成功完成。"""
        if not self._channel:
            raise RuntimeError("RabbitMQ 未连接")

        delivery_tag = self._pending_tags.pop(task_id, None)
        if delivery_tag is not None:
            await self._channel.basic_ack(delivery_tag)

    async def reject(self, task_id: str, requeue: bool = False) -> None:
        """拒绝任务(失败处理)。"""
        if not self._channel:
            raise RuntimeError("RabbitMQ 未连接")

        delivery_tag = self._pending_tags.pop(task_id, None)
        if delivery_tag is not None:
            await self._channel.basic_reject(delivery_tag, requeue=requeue)

    async def get_queue_size(self) -> int:
        """获取队列中的任务数量。"""
        if not self._queue:
            raise RuntimeError("RabbitMQ 未连接")

        queue_info = await self._queue.declare(passive=True)
        return queue_info.message_count

    async def clear(self) -> None:
        """清空队列中的所有任务。"""
        if not self._queue:
            raise RuntimeError("RabbitMQ 未连接")

        await self._queue.purge()
        self._pending_tags.clear()

    async def health_check(self) -> bool:
        """检查 RabbitMQ 健康状态。"""
        if not self._connection or self._connection.is_closed:
            return False

        try:
            # 尝试声明一个临时队列来测试连接
            if self._channel:
                await self._channel.declare_queue("health_check", auto_delete=True)
                return True
        except Exception:
            return False

        return False

    def __repr__(self) -> str:
        """字符串表示。"""
        return f"RabbitMQBackend(queue={self.queue_name})"
