"""基于 SQLite 的本地持久化队列后端。"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from chronflow.backends.base import QueueBackend


class SQLiteBackend(QueueBackend):
    """基于 SQLite 的本地持久化队列实现。

    特性:
    - 本地文件持久化,无需外部服务
    - 支持任务优先级和调度时间
    - 适合单机部署场景
    - 轻量级,零配置

    适用场景:
    - 开发环境和测试
    - 单机应用
    - 需要持久化但不需要分布式的场景
    """

    def __init__(
        self,
        db_path: str | Path = "chronflow.db",
        table_name: str = "task_queue",
    ) -> None:
        """初始化 SQLite 后端。

        Args:
            db_path: 数据库文件路径
            table_name: 任务队列表名
        """
        self.db_path = Path(db_path)
        self.table_name = table_name
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """连接到 SQLite 数据库并创建表。"""
        # 在线程池中执行同步操作
        await asyncio.to_thread(self._sync_connect)

    def _sync_connect(self) -> None:
        """同步连接数据库(在线程中执行)。"""
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit 模式
        )

        # 启用 WAL 模式提高并发性能
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

        # 创建任务队列表
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                task_id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                scheduled_time REAL NOT NULL,
                priority INTEGER DEFAULT 0,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                retry_count INTEGER DEFAULT 0
            )
            """
        )

        # 创建索引优化查询
        self._conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_scheduled_time
            ON {self.table_name}(scheduled_time, status, priority)
            """
        )

        self._conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_status
            ON {self.table_name}(status)
            """
        )

    async def disconnect(self) -> None:
        """关闭数据库连接。"""
        if self._conn:
            await asyncio.to_thread(self._conn.close)
            self._conn = None

    async def enqueue(
        self,
        task_id: str,
        task_name: str,
        scheduled_time: datetime,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """将任务添加到队列。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        async with self._lock:
            now = datetime.now().timestamp()
            scheduled_ts = scheduled_time.timestamp()

            await asyncio.to_thread(
                self._conn.execute,
                f"""
                INSERT OR REPLACE INTO {self.table_name}
                (task_id, task_name, scheduled_time, priority, payload,
                 status, created_at, updated_at, retry_count)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, 0)
                """,
                (
                    task_id,
                    task_name,
                    scheduled_ts,
                    priority,
                    json.dumps(payload),
                    now,
                    now,
                ),
            )

    async def dequeue(self, limit: int = 1) -> list[dict[str, Any]]:
        """从队列获取就绪的任务。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        async with self._lock:
            now = datetime.now().timestamp()

            # 查询就绪的任务(按优先级和调度时间排序)
            cursor = await asyncio.to_thread(
                self._conn.execute,
                f"""
                SELECT task_id, task_name, scheduled_time, priority, payload
                FROM {self.table_name}
                WHERE status = 'pending'
                  AND scheduled_time <= ?
                ORDER BY priority DESC, scheduled_time ASC
                LIMIT ?
                """,
                (now, limit),
            )

            rows = await asyncio.to_thread(cursor.fetchall)

            ready_tasks = []
            for row in rows:
                task_id, task_name, scheduled_ts, priority, payload_json = row

                # 标记为处理中
                await asyncio.to_thread(
                    self._conn.execute,
                    f"""
                    UPDATE {self.table_name}
                    SET status = 'processing', updated_at = ?
                    WHERE task_id = ?
                    """,
                    (now, task_id),
                )

                ready_tasks.append(
                    {
                        "task_id": task_id,
                        "task_name": task_name,
                        "scheduled_time": datetime.fromtimestamp(scheduled_ts).isoformat(),
                        "payload": json.loads(payload_json),
                        "priority": priority,
                    }
                )

            return ready_tasks

    async def acknowledge(self, task_id: str) -> None:
        """确认任务成功完成并从队列删除。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        async with self._lock:
            await asyncio.to_thread(
                self._conn.execute,
                f"""
                DELETE FROM {self.table_name}
                WHERE task_id = ?
                """,
                (task_id,),
            )

    async def reject(self, task_id: str, requeue: bool = False) -> None:
        """拒绝任务(失败处理)。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        async with self._lock:
            now = datetime.now().timestamp()

            if requeue:
                # 重新入队,增加重试计数
                await asyncio.to_thread(
                    self._conn.execute,
                    f"""
                    UPDATE {self.table_name}
                    SET status = 'pending',
                        retry_count = retry_count + 1,
                        updated_at = ?
                    WHERE task_id = ?
                    """,
                    (now, task_id),
                )
            else:
                # 标记为失败
                await asyncio.to_thread(
                    self._conn.execute,
                    f"""
                    UPDATE {self.table_name}
                    SET status = 'failed', updated_at = ?
                    WHERE task_id = ?
                    """,
                    (now, task_id),
                )

    async def get_queue_size(self) -> int:
        """获取队列中的任务数量。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        cursor = await asyncio.to_thread(
            self._conn.execute,
            f"""
            SELECT COUNT(*) FROM {self.table_name}
            WHERE status IN ('pending', 'processing')
            """,
        )

        row = await asyncio.to_thread(cursor.fetchone)
        return row[0] if row else 0

    async def clear(self) -> None:
        """清空队列中的所有任务。"""
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        async with self._lock:
            await asyncio.to_thread(
                self._conn.execute,
                f"DELETE FROM {self.table_name}",
            )

    async def health_check(self) -> bool:
        """检查数据库健康状态。"""
        if not self._conn:
            return False

        try:
            cursor = await asyncio.to_thread(
                self._conn.execute,
                "SELECT 1",
            )
            await asyncio.to_thread(cursor.fetchone)
            return True
        except Exception:
            return False

    async def get_failed_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取失败的任务列表。

        Args:
            limit: 返回的最大任务数

        Returns:
            失败任务列表
        """
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        cursor = await asyncio.to_thread(
            self._conn.execute,
            f"""
            SELECT task_id, task_name, scheduled_time, retry_count, payload
            FROM {self.table_name}
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = await asyncio.to_thread(cursor.fetchall)

        return [
            {
                "task_id": row[0],
                "task_name": row[1],
                "scheduled_time": datetime.fromtimestamp(row[2]).isoformat(),
                "retry_count": row[3],
                "payload": json.loads(row[4]),
            }
            for row in rows
        ]

    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务记录。

        Args:
            days: 保留最近多少天的任务

        Returns:
            删除的任务数量
        """
        if not self._conn:
            raise RuntimeError("SQLite 未连接")

        threshold = datetime.now().timestamp() - (days * 86400)

        async with self._lock:
            cursor = await asyncio.to_thread(
                self._conn.execute,
                f"""
                DELETE FROM {self.table_name}
                WHERE status = 'failed' AND updated_at < ?
                """,
                (threshold,),
            )

            return cursor.rowcount

    def __repr__(self) -> str:
        """字符串表示。"""
        return f"SQLiteBackend(db_path={self.db_path})"
