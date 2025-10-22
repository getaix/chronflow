# 队列后端

chronflow 支持多种队列后端，你可以根据应用场景选择合适的后端。

## 后端对比

| 后端 | 适用场景 | 持久化 | 分布式 | 性能 | 依赖 |
|------|---------|--------|--------|------|------|
| **Memory** | 开发、测试、单机 | ✗ | ✗ | ⭐⭐⭐⭐⭐ | 无 |
| **SQLite** | 单机生产、需要持久化 | ✓ | ✗ | ⭐⭐⭐⭐ | 无 |
| **Redis** | 分布式、高性能 | ✓ | ✓ | ⭐⭐⭐⭐⭐ | Redis |
| **RabbitMQ** | 高可靠性、消息队列 | ✓ | ✓ | ⭐⭐⭐⭐ | RabbitMQ |

## Memory Backend (内存队列)

### 特点

- ✅ 零外部依赖，开箱即用
- ✅ 性能最高，适合高频任务
- ✅ 适合开发和测试
- ❌ 重启后任务丢失
- ❌ 不支持分布式

### 使用方法

```python
from chronflow import Scheduler

# 默认使用内存后端
scheduler = Scheduler()
```

### 性能

- 吞吐量: 10000+ tasks/s
- 延迟: <1ms (p99)
- 内存占用: ~50MB

## SQLite Backend (本地持久化)

### 特点

- ✅ 本地文件持久化，重启不丢任务
- ✅ 零外部服务依赖
- ✅ 支持任务历史查询
- ✅ WAL 模式提升并发性能
- ❌ 不支持分布式

### 使用方法

```python
from chronflow import Scheduler
from chronflow.backends import SQLiteBackend

# 创建 SQLite 后端
backend = SQLiteBackend(db_path="scheduler.db")
scheduler = Scheduler(backend=backend)
```

### 配置选项

```python
backend = SQLiteBackend(
    db_path="scheduler.db",     # 数据库文件路径
    max_retries=3,               # 最大重试次数
    timeout=30.0                 # 超时时间（秒）
)
```

### 数据库结构

SQLiteBackend 会自动创建以下表结构：

```sql
CREATE TABLE task_queue (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    scheduled_time REAL NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    task_data TEXT NOT NULL,
    created_at REAL DEFAULT (julianday('now')),
    updated_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX idx_scheduled_time ON task_queue(scheduled_time);
CREATE INDEX idx_status ON task_queue(status);
```

### 性能

- 吞吐量: 5000+ tasks/s
- 延迟: <5ms (p99)
- 内存占用: ~80MB

### 清理历史数据

```python
from chronflow.backends import SQLiteBackend

backend = SQLiteBackend("scheduler.db")

# 清理7天前的已完成任务
await backend.cleanup_old_tasks(days=7)
```

## Redis Backend (分布式队列)

### 特点

- ✅ 支持分布式部署（多个调度器实例）
- ✅ 高性能，低延迟
- ✅ 数据持久化（取决于 Redis 配置）
- ✅ 支持集群模式
- ❌ 需要 Redis 服务

### 安装

```bash
pip install chronflow[redis]
```

### 使用方法

```python
from chronflow import Scheduler
from chronflow.backends import RedisBackend

# 创建 Redis 后端
backend = RedisBackend(url="redis://localhost:6379/0")
scheduler = Scheduler(backend=backend)
```

### 配置选项

```python
backend = RedisBackend(
    url="redis://localhost:6379/0",     # Redis 连接 URL
    key_prefix="chronflow:",            # 键前缀
    max_connections=10,                  # 最大连接数
    socket_timeout=5.0,                  # Socket 超时
    socket_connect_timeout=5.0,          # 连接超时
)
```

### Redis URL 格式

```python
# 基础连接
"redis://localhost:6379/0"

# 带密码
"redis://:password@localhost:6379/0"

# 带用户名和密码
"redis://username:password@localhost:6379/0"

# Redis Sentinel
"redis+sentinel://sentinel-host:26379/mymaster/0"

# Redis Cluster
"redis://localhost:7000,localhost:7001,localhost:7002/0"
```

### 性能

- 吞吐量: 8000+ tasks/s
- 延迟: <3ms (p99)
- 内存占用: ~60MB

### 数据结构

RedisBackend 使用以下 Redis 数据结构：

- **Sorted Set** (zset): 存储任务队列，按调度时间排序
- **Set**: 存储正在执行的任务 ID

```python
# 任务队列 (zset)
# Key: chronflow:queue
# Score: scheduled_time - priority*1000
# Member: JSON 序列化的任务数据

# 正在执行的任务 (set)
# Key: chronflow:pending
# Members: task IDs
```

## RabbitMQ Backend (消息队列)

### 特点

- ✅ 高可靠性消息队列
- ✅ 支持分布式部署
- ✅ 支持消息持久化
- ✅ 支持消息确认机制
- ❌ 需要 RabbitMQ 服务

### 安装

```bash
pip install chronflow[rabbitmq]
```

### 使用方法

```python
from chronflow import Scheduler
from chronflow.backends import RabbitMQBackend

# 创建 RabbitMQ 后端
backend = RabbitMQBackend(url="amqp://guest:guest@localhost:5672/")
scheduler = Scheduler(backend=backend)
```

### 配置选项

```python
backend = RabbitMQBackend(
    url="amqp://guest:guest@localhost:5672/",  # RabbitMQ 连接 URL
    queue_name="chronflow_tasks",             # 队列名称
    exchange_name="chronflow",                # 交换机名称
    durable=True,                              # 持久化队列
    max_priority=10,                           # 最大优先级
)
```

### RabbitMQ URL 格式

```python
# 基础连接
"amqp://guest:guest@localhost:5672/"

# 指定虚拟主机
"amqp://user:password@localhost:5672/my_vhost"

# 使用 TLS/SSL
"amqps://user:password@localhost:5671/"
```

### 性能

- 吞吐量: 6000+ tasks/s
- 延迟: <5ms (p99)
- 内存占用: ~70MB

## 自定义后端

你可以实现自己的队列后端：

```python
from chronflow.backends import QueueBackend
from chronflow.task import Task
from datetime import datetime
from typing import Optional

class MyCustomBackend(QueueBackend):
    """自定义队列后端。"""

    async def connect(self) -> None:
        """连接到后端。"""
        # 初始化连接
        pass

    async def disconnect(self) -> None:
        """断开连接。"""
        # 关闭连接
        pass

    async def enqueue(self, task: Task, scheduled_time: datetime,
                     priority: int = 0) -> None:
        """将任务加入队列。"""
        # 实现入队逻辑
        pass

    async def dequeue(self, max_items: int = 1) -> list[Task]:
        """从队列取出就绪任务。"""
        # 实现出队逻辑
        pass

    async def acknowledge(self, task: Task) -> None:
        """确认任务完成。"""
        # 实现确认逻辑
        pass

    async def reject(self, task: Task, requeue: bool = False) -> None:
        """拒绝任务（失败处理）。"""
        # 实现拒绝逻辑
        pass

    async def get_queue_size(self) -> int:
        """获取队列大小。"""
        # 返回队列中的任务数
        return 0

    async def clear(self) -> None:
        """清空队列。"""
        # 清空所有任务
        pass

    async def health_check(self) -> bool:
        """健康检查。"""
        # 检查后端是否正常
        return True

# 使用自定义后端
backend = MyCustomBackend()
scheduler = Scheduler(backend=backend)
```

## 后端选择建议

### 开发和测试
推荐使用 **Memory Backend**，零配置，性能最高。

### 单机生产环境
- 不需要持久化 → **Memory Backend**
- 需要持久化 → **SQLite Backend**

### 分布式生产环境
- 高性能要求 → **Redis Backend**
- 高可靠性要求 → **RabbitMQ Backend**

### 特殊场景
- 已有 Redis → **Redis Backend**
- 已有 RabbitMQ → **RabbitMQ Backend**
- 完全离线环境 → **SQLite Backend**
- 极致性能 → **Memory Backend**

## 后端迁移

从一个后端迁移到另一个后端：

```python
from chronflow import Scheduler
from chronflow.backends import MemoryBackend, SQLiteBackend

# 旧调度器（内存后端）
old_scheduler = Scheduler(backend=MemoryBackend())

# 新调度器（SQLite 后端）
new_backend = SQLiteBackend("scheduler.db")
new_scheduler = Scheduler(backend=new_backend)

# 迁移任务
for task_name in old_scheduler._tasks:
    task = old_scheduler.get_task(task_name)
    new_scheduler.register_task(task)

# 停止旧调度器，启动新调度器
await old_scheduler.stop()
await new_scheduler.start()
```
