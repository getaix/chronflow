# Symphra Scheduler

A lightweight, async-first scheduler for Python with a clean decorator API, second-level Cron support, and rich observability. This page mirrors the Chinese index for full consistency.

## Features

### Cron with seconds
Supports standard Cron expressions extended to seconds precision to meet high-frequency scheduling needs.

### Multiple backends
- Memory — zero dependency, instant start
- SQLite — local persistence, tasks survive restarts
- Redis — distributed, high performance
- RabbitMQ — high reliability message queue

### Simple API
Define tasks with one line using decorators:

```python
@cron("*/5 * * * * *")  # every 5 seconds
async def my_task():
    print("running...")
```

### Smart retries
Built-in retry powered by Tenacity:
- Exponential backoff (great for network calls)
- Fixed intervals (good for polling)
- Random intervals (avoid thundering herd)

### Type safety
100% type hints coverage with strong IDE support.

## Installation

```bash
# Base install (Memory/SQLite backends)
pip install symphra-scheduler

# Redis support
pip install symphra-scheduler[redis]

# RabbitMQ support
pip install symphra-scheduler[rabbitmq]

# All backends
pip install symphra-scheduler[all]
```

## 5-minute Quickstart

```python
import asyncio
from symphra_scheduler import Scheduler, cron, interval

scheduler = Scheduler()

@cron("*/5 * * * * *")  # every 5 seconds
async def health_check():
    print("health check...")

@interval(60)  # every 60 seconds
async def sync_data():
    print("syncing data...")

async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

See [Quickstart](quickstart.md) for more examples.

## License

MIT License
