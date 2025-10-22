"""Redis 后端 mock 测试。"""

import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock redis.asyncio module before importing RedisBackend
mock_redis = MagicMock()
sys.modules["redis"] = mock_redis
sys.modules["redis.asyncio"] = mock_redis


class TestRedisBackendMocked:
    """Redis 后端 mock 测试类。"""

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_connect(self, mock_redis_class):
        """测试连接 Redis。"""
        from chronflow.backends.redis_backend import RedisBackend

        # 创建 mock Redis 实例
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        # 验证 Redis.from_url 被调用
        mock_redis_class.from_url.assert_called_once()
        # 验证 ping 被调用
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_disconnect(self, mock_redis_class):
        """测试断开 Redis 连接。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()
        await backend.disconnect()

        # 验证 close 被调用
        mock_redis.close.assert_called_once()
        assert backend._redis is None

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_enqueue(self, mock_redis_class):
        """测试入队。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.zadd = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        now = datetime.now()
        await backend.enqueue(
            task_id="task1",
            task_name="test_task",
            scheduled_time=now,
            payload={"data": "test"},
            priority=0,
        )

        # 验证 zadd 被调用
        mock_redis.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_without_connection(self):
        """测试未连接时入队。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(),
                payload={},
                priority=0,
            )

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_dequeue(self, mock_redis_class):
        """测试出队。"""
        import json

        from chronflow.backends.redis_backend import RedisBackend

        # 创建 mock task JSON
        task_json = json.dumps(
            {
                "task_id": "task1",
                "task_name": "test",
                "payload": {},
            }
        )

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[task_json])

        # Mock pipeline
        mock_pipe = AsyncMock()
        mock_pipe.zrem = MagicMock()
        mock_pipe.sadd = MagicMock()
        mock_pipe.execute = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        tasks = await backend.dequeue(limit=1)

        # 验证 zrangebyscore 被调用
        mock_redis.zrangebyscore.assert_called_once()
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task1"

    @pytest.mark.asyncio
    async def test_dequeue_without_connection(self):
        """测试未连接时出队。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.dequeue(limit=1)

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_acknowledge(self, mock_redis_class):
        """测试确认任务。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.srem = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        await backend.acknowledge("task1")

        # 验证 srem 被调用
        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_without_connection(self):
        """测试未连接时确认。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.acknowledge("task1")

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_reject(self, mock_redis_class):
        """测试拒绝任务。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.srem = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        await backend.reject("task1", requeue=False)

        # 验证 srem 被调用
        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_without_connection(self):
        """测试未连接时拒绝。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.reject("task1", requeue=False)

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_get_queue_size(self, mock_redis_class):
        """测试获取队列大小。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=3)
        mock_redis.scard = AsyncMock(return_value=2)
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        size = await backend.get_queue_size()

        assert size == 5  # 3 + 2
        mock_redis.zcard.assert_called_once()
        mock_redis.scard.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_queue_size_without_connection(self):
        """测试未连接时获取队列大小。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.get_queue_size()

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_clear(self, mock_redis_class):
        """测试清空队列。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        # Mock pipeline
        mock_pipe = AsyncMock()
        mock_pipe.delete = MagicMock()
        mock_pipe.execute = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        await backend.clear()

        # 验证 delete 被调用了两次(queue 和 pending set)
        assert mock_pipe.delete.call_count == 2
        mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_without_connection(self):
        """测试未连接时清空队列。"""
        from chronflow.backends.redis_backend import RedisBackend

        backend = RedisBackend()

        with pytest.raises(RuntimeError, match="Redis not connected"):
            await backend.clear()

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_health_check(self, mock_redis_class):
        """测试健康检查。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        result = await backend.health_check()

        assert result is True
        # ping 应该被调用两次: 一次在 connect, 一次在 health_check
        assert mock_redis.ping.call_count == 2

    @pytest.mark.asyncio
    @patch("chronflow.backends.redis_backend.Redis")
    async def test_health_check_failure(self, mock_redis_class):
        """测试健康检查失败。"""
        from chronflow.backends.redis_backend import RedisBackend

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=[None, Exception("Connection lost")])
        mock_redis_class.from_url.return_value = mock_redis

        backend = RedisBackend()
        await backend.connect()

        result = await backend.health_check()

        assert result is False
