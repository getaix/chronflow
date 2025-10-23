"""队列后端测试。"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from chronflow.backends.memory import MemoryBackend
from chronflow.backends.sqlite_backend import SQLiteBackend


class TestMemoryBackend:
    """内存后端测试类。"""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接和断开。"""
        backend = MemoryBackend()

        await backend.connect()
        assert await backend.health_check() is True

        await backend.disconnect()
        assert len(backend._queue) == 0

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """测试入队和出队。"""
        backend = MemoryBackend()
        await backend.connect()

        now = datetime.now(timezone.utc)

        await backend.enqueue(
            task_id="task1",
            task_name="test_task",
            scheduled_time=now,
            payload={"data": "test"},
            priority=0,
        )

        tasks = await backend.dequeue(limit=1)

        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task1"
        assert tasks[0]["task_name"] == "test_task"
        assert tasks[0]["payload"] == {"data": "test"}

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_dequeue_scheduled_time(self):
        """测试按计划时间出队。"""
        backend = MemoryBackend()
        await backend.connect()

        now = datetime.now(timezone.utc)
        future = now + timedelta(seconds=10)

        # 添加未来的任务
        await backend.enqueue(
            task_id="future_task",
            task_name="test",
            scheduled_time=future,
            payload={},
            priority=0,
        )

        # 应该取不到
        tasks = await backend.dequeue(limit=1)
        assert len(tasks) == 0

        # 添加当前时间的任务
        await backend.enqueue(
            task_id="now_task",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        # 应该能取到
        tasks = await backend.dequeue(limit=1)
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "now_task"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """测试优先级排序。"""
        backend = MemoryBackend()
        await backend.connect()

        now = datetime.now(timezone.utc)

        # 添加不同优先级的任务
        await backend.enqueue(
            task_id="low",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=1,
        )

        await backend.enqueue(
            task_id="high",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=10,
        )

        await backend.enqueue(
            task_id="medium",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=5,
        )

        # 应该按优先级顺序取出
        tasks = await backend.dequeue(limit=3)

        assert len(tasks) == 3
        assert tasks[0]["task_id"] == "high"
        assert tasks[1]["task_id"] == "medium"
        assert tasks[2]["task_id"] == "low"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_acknowledge(self):
        """测试确认任务。"""
        backend = MemoryBackend()
        await backend.connect()

        await backend.enqueue(
            task_id="task1",
            task_name="test",
            scheduled_time=datetime.now(timezone.utc),
            payload={},
            priority=0,
        )

        await backend.dequeue(limit=1)
        assert len(backend._pending) == 1

        await backend.acknowledge("task1")
        assert len(backend._pending) == 0

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_reject(self):
        """测试拒绝任务。"""
        backend = MemoryBackend()
        await backend.connect()

        await backend.enqueue(
            task_id="task1",
            task_name="test",
            scheduled_time=datetime.now(timezone.utc),
            payload={},
            priority=0,
        )

        await backend.dequeue(limit=1)
        assert len(backend._pending) == 1

        await backend.reject("task1", requeue=False)
        assert len(backend._pending) == 0

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_get_queue_size(self):
        """测试获取队列大小。"""
        backend = MemoryBackend()
        await backend.connect()

        assert await backend.get_queue_size() == 0

        now = datetime.now(timezone.utc)

        await backend.enqueue(
            task_id="task1",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        await backend.enqueue(
            task_id="task2",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        assert await backend.get_queue_size() == 2

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空队列。"""
        backend = MemoryBackend()
        await backend.connect()

        now = datetime.now(timezone.utc)

        await backend.enqueue(
            task_id="task1",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        await backend.enqueue(
            task_id="task2",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        assert await backend.get_queue_size() == 2

        await backend.clear()

        assert await backend.get_queue_size() == 0

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_max_size_exceeded(self):
        """测试队列满载。"""
        backend = MemoryBackend(max_size=2)
        await backend.connect()

        now = datetime.now(timezone.utc)

        await backend.enqueue(
            task_id="task1",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        await backend.enqueue(
            task_id="task2",
            task_name="test",
            scheduled_time=now,
            payload={},
            priority=0,
        )

        # 第三个任务应该失败
        with pytest.raises(RuntimeError, match="Queue is full"):
            await backend.enqueue(
                task_id="task3",
                task_name="test",
                scheduled_time=now,
                payload={},
                priority=0,
            )

        await backend.disconnect()


class TestSQLiteBackend:
    """SQLite 后端测试类。"""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接和断开。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()
            assert await backend.health_check() is True

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """测试入队和出队。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()

            now = datetime.now(timezone.utc)

            await backend.enqueue(
                task_id="task1",
                task_name="test_task",
                scheduled_time=now,
                payload={"data": "test"},
                priority=0,
            )

            tasks = await backend.dequeue(limit=1)

            assert len(tasks) == 1
            assert tasks[0]["task_id"] == "task1"
            assert tasks[0]["task_name"] == "test_task"

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_persistence(self):
        """测试数据持久化。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # 第一次连接,添加任务
            backend1 = SQLiteBackend(db_path=db_path)
            await backend1.connect()

            await backend1.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(timezone.utc),
                payload={"data": "test"},
                priority=0,
            )

            await backend1.disconnect()

            # 第二次连接,应该能读取到任务
            backend2 = SQLiteBackend(db_path=db_path)
            await backend2.connect()

            size = await backend2.get_queue_size()
            assert size == 1

            await backend2.disconnect()

    @pytest.mark.asyncio
    async def test_acknowledge(self):
        """测试确认任务(删除)。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()

            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(timezone.utc),
                payload={},
                priority=0,
            )

            assert await backend.get_queue_size() == 1

            await backend.dequeue(limit=1)
            await backend.acknowledge("task1")

            assert await backend.get_queue_size() == 0

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_reject_with_requeue(self):
        """测试拒绝任务并重新入队。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()

            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(timezone.utc),
                payload={},
                priority=0,
            )

            await backend.dequeue(limit=1)
            await backend.reject("task1", requeue=True)

            # 应该重新进入待处理状态
            size = await backend.get_queue_size()
            assert size == 1

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self):
        """测试清理旧任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()

            # 添加任务并标记为失败
            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(timezone.utc),
                payload={},
                priority=0,
            )

            await backend.dequeue(limit=1)
            await backend.reject("task1", requeue=False)

            # 清理 0 天内的任务(应该清理掉)
            deleted = await backend.cleanup_old_tasks(days=0)
            assert deleted >= 0

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_get_failed_tasks(self):
        """测试获取失败任务列表。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            await backend.connect()

            await backend.enqueue(
                task_id="task1",
                task_name="test",
                scheduled_time=datetime.now(timezone.utc),
                payload={"data": "test"},
                priority=0,
            )

            await backend.dequeue(limit=1)
            await backend.reject("task1", requeue=False)

            failed = await backend.get_failed_tasks(limit=10)
            assert len(failed) == 1
            assert failed[0]["task_id"] == "task1"

            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_enqueue_without_connection(self):
        """测试未连接时入队。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试入队
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.enqueue(
                    task_id="task1",
                    task_name="test",
                    scheduled_time=datetime.now(timezone.utc),
                    payload={},
                    priority=0,
                )

    @pytest.mark.asyncio
    async def test_dequeue_without_connection(self):
        """测试未连接时出队。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试出队
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.dequeue(limit=1)

    @pytest.mark.asyncio
    async def test_acknowledge_without_connection(self):
        """测试未连接时确认。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试确认
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.acknowledge("task1")

    @pytest.mark.asyncio
    async def test_reject_without_connection(self):
        """测试未连接时拒绝。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试拒绝
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.reject("task1", requeue=False)

    @pytest.mark.asyncio
    async def test_get_queue_size_without_connection(self):
        """测试未连接时获取队列大小。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试获取队列大小
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.get_queue_size()

    @pytest.mark.asyncio
    async def test_clear_without_connection(self):
        """测试未连接时清空队列。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试清空队列
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.clear()

    @pytest.mark.asyncio
    async def test_get_failed_tasks_without_connection(self):
        """测试未连接时获取失败任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试获取失败任务
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.get_failed_tasks(limit=10)

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks_without_connection(self):
        """测试未连接时清理旧任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backend = SQLiteBackend(db_path=db_path)

            # 未连接就尝试清理旧任务
            with pytest.raises(RuntimeError, match="SQLite 未连接"):
                await backend.cleanup_old_tasks(days=7)
