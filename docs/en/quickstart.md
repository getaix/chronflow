# Symphra Scheduler Quickstart

This quickstart mirrors the Chinese version and guides you through installation, defining tasks, cron expressions, retries, persistence, distributed deployment, and common scenarios.

## 1. Install

Using uv (recommended):
```bash
uv pip install symphra-scheduler
```

Using pip:
```bash
pip install symphra-scheduler
```

Optional backends:
```bash
# Redis support
pip install symphra-scheduler[redis]

# RabbitMQ support
pip install symphra-scheduler[rabbitmq]

# All backends
pip install symphra-scheduler[all]
```

## 2. First scheduled task

Create `app.py`:

```python
import asyncio
from symphra_scheduler import Scheduler, interval

scheduler = Scheduler()

@interval(5)  # every 5 seconds
async def hello_task():
    print("Hello, Symphra Scheduler!")

async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

Run:
```bash
python app.py
```

## 3. Cron expressions

```python
from symphra_scheduler import cron

@cron("0 0 9 * * *")  # every day at 09:00
async def daily_report():
    print("Generating daily report...")

@cron("*/5 * * * * *")  # every 5 seconds
async def health_check():
    print("Health check...")
```

## 4. Retry policy

```python
from symphra_scheduler import interval, RetryPolicy

@interval(
    30,
    retry_policy=RetryPolicy(
        max_attempts=5,
        strategy="exponential",
        wait_min=1.0,
        wait_max=60.0,
    )
)
async def important_task():
    await do_something_critical()
```

## 5. Persistent queue (SQLite)

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.backends import SQLiteBackend

backend = SQLiteBackend(db_path="tasks.db")
scheduler = Scheduler(backend=backend)

@interval(60)
async def persistent_task():
    print("This task is persisted!")
```

## 6. Distributed deployment (Redis)

```bash
uv pip install symphra-scheduler[redis]
```

```python
from symphra_scheduler import Scheduler, SchedulerConfig
from symphra_scheduler.backends import RedisBackend

backend = RedisBackend(url="redis://localhost:6379/0")
config = SchedulerConfig(max_workers=20)

scheduler = Scheduler(config=config, backend=backend)

@interval(10)
async def distributed_task():
    print("Distributed task running...")
```

## 7. Common scenarios

### Data sync

```python
@interval(300)  # every 5 minutes
async def sync_data():
    data = await fetch_from_api()
    await save_to_database(data)
```

### Periodic cleanup

```python
@cron("0 0 2 * * *")  # every day at 02:00
async def cleanup():
    await delete_old_records()
```

### Health monitoring

```python
@interval(30)
async def monitor_services():
    for service in services:
        if not await service.is_healthy():
            await send_alert(f"{service.name} is unhealthy!")
```

### Report generation

```python
@daily(hour=6, minute=0)
async def generate_reports():
    await build_daily_reports()
    await notify_team()
```

## Next steps

- Check [Home](index.md) for full features
- Explore [guides](guides/) like [Backends](guides/backends.md), [Logging](guides/logging.md), [Monitoring](guides/monitoring.md)
- Browse [examples](https://github.com/getaix/symphra-scheduler/tree/main/examples/)
- Read [Contributing](contributing.md) to contribute
