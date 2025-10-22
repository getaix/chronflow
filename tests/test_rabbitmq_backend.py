"""RabbitMQ 后端 mock 测试。"""

import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock aio_pika module before importing RabbitMQBackend
mock_aio_pika = MagicMock()
sys.modules["aio_pika"] = mock_aio_pika
sys.modules["aio_pika.abc"] = MagicMock()


class TestRabbitMQBackendMocked:
    """RabbitMQ 后端 mock 测试类。"""

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_connect(self, mock_connect):
        """测试连接 RabbitMQ。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        # 创建 mock 对象
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        # 验证 connect_robust 被调用
        mock_connect.assert_called_once()
        # 验证 set_qos 被调用
        mock_channel.set_qos.assert_called_once()
        # 验证 declare_queue 被调用
        mock_channel.declare_queue.assert_called_once()

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_disconnect(self, mock_connect):
        """测试断开 RabbitMQ 连接。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_connection.close = AsyncMock()

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()
        await backend.disconnect()

        # 验证 close 被调用
        mock_connection.close.assert_called_once()
        assert backend._connection is None

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    @patch("chronflow.backends.rabbitmq_backend.Message")
    async def test_enqueue(self, mock_message_class, mock_connect):
        """测试入队。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        mock_message = MagicMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_channel.default_exchange.publish = AsyncMock()

        mock_message_class.return_value = mock_message
        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        now = datetime.now()
        await backend.enqueue(
            task_id="task1",
            task_name="test_task",
            scheduled_time=now,
            payload={"data": "test"},
            priority=0,
        )

        # 验证 Message 被创建
        mock_message_class.assert_called_once()
        # 验证 publish 被调用
        mock_channel.default_exchange.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_without_connection(self):
        """测试未连接时入队。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(),
                payload={},
                priority=0,
            )

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_dequeue(self, mock_connect):
        """测试出队。"""
        import json

        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        # 创建 mock message
        mock_message = AsyncMock()
        mock_message.delivery_tag = 1
        mock_message.body = json.dumps(
            {
                "task_id": "task1",
                "task_name": "test",
                "payload": {},
            }
        ).encode()

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        # 第一次返回消息,第二次返回None
        mock_queue.get = AsyncMock(side_effect=[mock_message, None])

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        tasks = await backend.dequeue(limit=1)

        # 验证 get 被调用
        mock_queue.get.assert_called()
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task1"

    @pytest.mark.asyncio
    async def test_dequeue_without_connection(self):
        """测试未连接时出队。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.dequeue(limit=1)

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_acknowledge(self, mock_connect):
        """测试确认任务。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_channel.basic_ack = AsyncMock()

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        # 模拟已有 pending tag
        backend._pending_tags["task1"] = 1

        await backend.acknowledge("task1")

        # 验证 basic_ack 被调用
        mock_channel.basic_ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_without_connection(self):
        """测试未连接时确认。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.acknowledge("task1")

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_reject(self, mock_connect):
        """测试拒绝任务。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_channel.basic_reject = AsyncMock()

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        # 模拟已有 pending tag
        backend._pending_tags["task1"] = 1

        await backend.reject("task1", requeue=False)

        # 验证 basic_reject 被调用
        mock_channel.basic_reject.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_without_connection(self):
        """测试未连接时拒绝。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.reject("task1", requeue=False)

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_get_queue_size(self, mock_connect):
        """测试获取队列大小。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        # Mock queue.declare to return a queue with message_count
        mock_queue_info = MagicMock()
        mock_queue_info.message_count = 5
        mock_queue.declare = AsyncMock(return_value=mock_queue_info)

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        size = await backend.get_queue_size()

        assert size == 5
        mock_queue.declare.assert_called_once_with(passive=True)

    @pytest.mark.asyncio
    async def test_get_queue_size_without_connection(self):
        """测试未连接时获取队列大小。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.get_queue_size()

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_clear(self, mock_connect):
        """测试清空队列。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_queue.purge = AsyncMock()

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        await backend.clear()

        # 验证 purge 被调用
        mock_queue.purge.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_without_connection(self):
        """测试未连接时清空队列。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        backend = RabbitMQBackend()

        with pytest.raises(RuntimeError, match="RabbitMQ 未连接"):
            await backend.clear()

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_health_check(self, mock_connect):
        """测试健康检查。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        mock_connection.is_closed = False

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        result = await backend.health_check()

        assert result is True

    @pytest.mark.asyncio
    @patch("chronflow.backends.rabbitmq_backend.connect_robust", new_callable=AsyncMock)
    async def test_health_check_failure(self, mock_connect):
        """测试健康检查失败。"""
        from chronflow.backends.rabbitmq_backend import RabbitMQBackend

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        mock_connection.is_closed = True  # 连接已关闭

        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.set_qos = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        mock_connect.return_value = mock_connection

        backend = RabbitMQBackend()
        await backend.connect()

        result = await backend.health_check()

        assert result is False
