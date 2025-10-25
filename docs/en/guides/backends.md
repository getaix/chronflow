# Queue Backends

Symphra Scheduler supports multiple queue backends. Choose the right backend based on your deployment scenario.

## Backend Comparison

| Backend   | Best for                    | Persistence | Distributed | Performance | Dependency |
|-----------|-----------------------------|-------------|-------------|-------------|------------|
| Memory    | Development, testing, single host | ✗       | ✗           | ⭐⭐⭐⭐⭐       | None       |
| SQLite    | Single-host production with persistence | ✓ | ✗         | ⭐⭐⭐⭐        | None       |
| Redis     | Distributed, high throughput | ✓          | ✓           | ⭐⭐⭐⭐⭐       | Redis      |
| RabbitMQ  | High reliability MQ          | ✓          | ✓           | ⭐⭐⭐⭐        | RabbitMQ   |

## Memory Backend (in-memory queue)

### Features

- Zero external dependencies, works out of the box
- Highest performance, ideal for high-frequency tasks
- Perfect for development and testing
- Not persistent; tasks are lost on restart
- Not suitable for distributed deployments

### Usage

```python
from symphra_scheduler import Scheduler

# Default is memory backend
scheduler = Scheduler()
```

### Performance

- Throughput: 10,000+ tasks/s
- Latency: <1ms (p99)
- Memory: ~50MB

## SQLite Backend (local persistence)

### Features

- Persistent local file; tasks survive restarts
- No external services required
- Supports task history queries
- Better concurrent performance with WAL mode
- Not suitable for distributed deployments

### Usage

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.backends import SQLiteBackend

backend = SQLiteBackend(db_path="scheduler.db")
scheduler = Scheduler(backend=backend)
```

### Configuration Options

```python
from symphra_scheduler.backends import SQLiteBackend

backend = SQLiteBackend(
    db_path="scheduler.db",   # Database file path (default: symphra_scheduler.db)
    table_name="task_queue",  # Queue table name (default: task_queue)
)
```

### Performance

- Throughput: 8,000+ tasks/s
- Latency: <3ms (p99)
- Memory: ~60MB

### Data Schema

SQLiteBackend uses a single table with indexes optimized for querying and updating ready tasks:

```sql
-- Task queue table
CREATE TABLE IF NOT EXISTS task_queue (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    scheduled_time REAL NOT NULL,
    priority INTEGER DEFAULT 0,
    payload TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    retry_count INTEGER DEFAULT 0
);

-- Query optimization indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_time
ON task_queue(scheduled_time, status, priority);

CREATE INDEX IF NOT EXISTS idx_status
ON task_queue(status);
```

## Redis Backend (distributed queue)

### Features

- Suitable for distributed deployments and high-concurrency scenarios
- Strong persistence; tasks survive restarts
- High-performance data structures provided by Redis

### Installation

```bash
pip install symphra-scheduler[redis]
```

### Usage

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.backends import RedisBackend

backend = RedisBackend(url="redis://localhost:6379/0")
scheduler = Scheduler(backend=backend)
```

### Configuration Options

```python
from symphra_scheduler.backends import RedisBackend

backend = RedisBackend(
    url="redis://localhost:6379/0",  # Redis connection URL
    queue_name="symphra_scheduler:queue",  # Queue (zset) key
    pending_set="symphra_scheduler:pending",  # In-flight tasks (set) key
    max_connections=10,  # Max connections in pool
)
```

### Redis URL Formats

```python
# Basic
"redis://localhost:6379/0"

# With password
"redis://:password@localhost:6379/0"

# With username and password
"redis://username:password@localhost:6379/0"

# Redis Sentinel
"redis+sentinel://sentinel-host:26379/mymaster/0"

# Redis Cluster
"redis://localhost:7000,localhost:7001,localhost:7002/0"
```

### Data Structures

RedisBackend uses:

- Sorted Set (zset): queue ordered by schedule time
- Set: in-flight task IDs

```python
# Queue (zset)
# Key: symphra_scheduler:queue
# Score: scheduled_time - priority*1000
# Member: JSON-serialized task data

# In-flight tasks (set)
# Key: symphra_scheduler:pending
# Members: task IDs
```

## RabbitMQ Backend (message queue)

### Features

- High reliability message queue
- Supports distributed deployments
- Message persistence
- Message acknowledgment mechanisms
- Requires a RabbitMQ server

### Installation

```bash
pip install symphra-scheduler[rabbitmq]
```

### Usage

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.backends import RabbitMQBackend

backend = RabbitMQBackend(url="amqp://guest:guest@localhost:5672/")
scheduler = Scheduler(backend=backend)
```

### Configuration Options

```python
backend = RabbitMQBackend(
    url="amqp://guest:guest@localhost:5672/",   # RabbitMQ connection URL
    queue_name="symphra_scheduler_tasks",        # Queue name
    exchange_name="symphra_scheduler",           # Exchange name
    durable=True,                                 # Durable queue
    max_priority=10,                              # Max priority
)
```

### RabbitMQ URL Formats

```python
# Basic
"amqp://guest:guest@localhost:5672/"

# Virtual host
"amqp://user:password@localhost:5672/my_vhost"

# TLS/SSL
"amqps://user:password@localhost:5671/"
```

### Performance

- Throughput: 6,000+ tasks/s
- Latency: <5ms (p99)
- Memory: ~70MB

## Custom Backend

You can implement your own backend:

```python
from symphra_scheduler.backends import QueueBackend
from symphra_scheduler.task import Task
from datetime import datetime
from typing import Optional

class MyCustomBackend(QueueBackend):
    """Custom queue backend."""

    async def connect(self) -> None:
        """Connect to backend."""
        # Initialize connection
        pass

    async def disconnect(self) -> None:
        """Disconnect from backend."""
        # Close connection
        pass

    async def enqueue(self, task: Task, scheduled_time: datetime,
                      priority: int = 0) -> None:
        """Enqueue a task."""
        # Implement enqueue logic
        pass

    async def dequeue(self, max_items: int = 1) -> list[Task]:
        """Dequeue ready tasks."""
        # Implement dequeue logic
        return []

    async def acknowledge(self, task: Task) -> None:
        """Acknowledge completion."""
        # Implement ack logic
        pass

    async def reject(self, task: Task, requeue: bool = False) -> None:
        """Reject task (failure handling)."""
        # Implement reject logic
        pass

    async def get_queue_size(self) -> int:
        """Return queue size."""
        # Return number of tasks in queue
        return 0

    async def clear(self) -> None:
        """Clear the queue."""
        # Clear all tasks
        pass

    async def health_check(self) -> bool:
        """Backend health check."""
        # Check backend health
        return True

# Use custom backend
backend = MyCustomBackend()
scheduler = Scheduler(backend=backend)
```

## Backend Selection Guide

### Development and Testing
Use **Memory Backend** — zero config, highest performance.

### Single-host Production
- No persistence needed → **Memory Backend**
- Persistence needed → **SQLite Backend**

### Distributed Production
- High performance → **Redis Backend**
- High reliability → **RabbitMQ Backend**

### Special Cases
- Existing Redis → **Redis Backend**
- Existing RabbitMQ → **RabbitMQ Backend**
- Fully offline → **SQLite Backend**
- Extreme performance → **Memory Backend**

## Migrating Backends

Migrate from one backend to another:

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.backends import MemoryBackend, SQLiteBackend

# Old scheduler (memory backend)
old_scheduler = Scheduler(backend=MemoryBackend())

# New scheduler (SQLite backend)
new_backend = SQLiteBackend("scheduler.db")
new_scheduler = Scheduler(backend=new_backend)

# Migrate tasks
for task_name in old_scheduler._tasks:
    task = old_scheduler.get_task(task_name)
    new_scheduler.register_task(task)

# Stop old scheduler, start new one
await old_scheduler.stop()
await new_scheduler.start()
```
