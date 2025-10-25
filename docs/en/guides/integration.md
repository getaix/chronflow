# Integration Guide

This guide explains how to integrate Symphra Scheduler correctly in real projects and keep behavior consistent with the Chinese documentation. It covers recommended patterns, configuration, monitoring, logging, performance tuning, best practices, troubleshooting, and upgrade notes.

## Overview

Symphra Scheduler is a lightweight, async-first scheduler. You can embed it inside your application, run it as a standalone daemon, or start it in the foreground during development. The goal is reliable task execution with clear observability.

## Common Issues and Solutions

### Duplicate task execution

- Define tasks at module top-level (not inside functions)
- Avoid registering tasks in request handlers or runtime branches
- Ensure each task has a unique `name`

```python
from symphra_scheduler import interval

@interval(seconds=10, name="my_task")
async def my_task():
    print("running...")
```

### Ctrl+C cannot stop

- Use v0.2.1+ or newer, which registers proper signal handlers for foreground mode
- On Windows, prefer graceful shutdown via `await scheduler.stop()`

```bash
pip install --upgrade symphra-scheduler
```

### Daemon logs printed to terminal

- From v0.2.1+, daemon mode detaches correctly
- Or redirect output manually

```bash
python your_script.py > /dev/null 2>&1 &
```

## Integration Patterns

### A) Embed inside an async application (FastAPI/Quart/Sanic)

```python
import asyncio
from symphra_scheduler import Scheduler, interval

@interval(seconds=30)
async def health_check():
    print("health check...")

class Application:
    def __init__(self):
        self.scheduler = Scheduler()

    async def startup(self):
        asyncio.create_task(self.scheduler.start())
        print("scheduler started")

    async def shutdown(self):
        await self.scheduler.stop()
        print("scheduler stopped")
```

- Start the scheduler on app startup
- Stop it gracefully on shutdown
- Avoid blocking the main event loop

### B) Standalone daemon process

```python
# scheduler_daemon.py
import asyncio
from symphra_scheduler import Scheduler, interval

@interval(seconds=60)
async def cleanup_task():
    print("cleanup...")

async def main():
    scheduler = Scheduler()
    pid = await scheduler.start(daemon=True)
    print(f"daemon started, PID: {pid}")

if __name__ == "__main__":
    asyncio.run(main())
```

- Suitable for production deployments
- Detaches from terminal; monitor via logs and metrics

### C) Foreground mode (development)

```python
# scheduler_foreground.py
import asyncio
from symphra_scheduler import Scheduler, cron

@cron("*/5 * * * * *")
async def log_task():
    print("logging...")

async def main():
    scheduler = Scheduler()
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

- Runs in the foreground with Ctrl+C handling
- Ideal for local development and debugging

## Configuration Management

You can configure the scheduler programmatically, via environment variables, or with YAML files.

### Programmatic configuration

```python
from symphra_scheduler import Scheduler, SchedulerConfig

config = SchedulerConfig(
    max_workers=10,
    queue_size=1000,
    timezone="UTC",
)

scheduler = Scheduler(config)
```

### Environment variables (example)

```bash
export SCHEDULER_MAX_WORKERS=20
export SCHEDULER_QUEUE_SIZE=2000
export SCHEDULER_TIMEZONE=Asia/Shanghai
```

Load them in your app and construct `SchedulerConfig` accordingly.

### YAML configuration (example)

```yaml
scheduler:
  max_workers: 16
  queue_size: 1500
  timezone: Asia/Shanghai
backend:
  type: redis
  url: redis://localhost:6379/0
  max_connections: 50
```

```python
import yaml
from symphra_scheduler import Scheduler, SchedulerConfig
from symphra_scheduler.backends import RedisBackend

with open("config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

backend = RedisBackend(
    url=cfg["backend"]["url"],
    max_connections=cfg["backend"].get("max_connections", 10),
)

config = SchedulerConfig(**cfg["scheduler"])  # type: ignore[arg-type]
scheduler = Scheduler(config=config, backend=backend)
```

## Monitoring and Debugging

Use built-in methods to inspect scheduler and tasks.

```python
from symphra_scheduler import Scheduler, TaskStatus

scheduler = Scheduler()

# Scheduler stats
stats = await scheduler.get_stats()
print(stats)

# List tasks
for t in scheduler.list_tasks():
    print(t)

# Filter by status
failed = scheduler.get_task_by_status(TaskStatus.FAILED)

# Control tasks
await scheduler.pause_task("health_check")
await scheduler.resume_task("health_check")
```

For a complete walkthrough, see the Monitoring guide.

## Logging Configuration

Symphra Scheduler supports multiple logging adapters:

- Structlog
- Loguru
- Python standard `logging`
- No-op adapter to disable logs entirely

Examples:

```python
from symphra_scheduler.logging import StructlogAdapter
import structlog

logger = structlog.get_logger()
scheduler = Scheduler(logger=StructlogAdapter(logger))
```

```python
from symphra_scheduler.logging import LoguruAdapter
from loguru import logger

logger.add("scheduler.log", format="{time} {level} {message}")
scheduler = Scheduler(logger=LoguruAdapter(logger))
```

To reduce log volume in production, prefer INFO level for scheduler lifecycle and WARN/ERROR for failures.

## Performance Optimization

- `max_workers`: increase for more concurrency within resource limits
- Backend choice:
  - Memory: highest throughput, no persistence
  - SQLite: local persistence on single host
  - Redis: distributed, high performance
  - RabbitMQ: high reliability message queue
- `queue_size`: size of in-memory queue for ingestion
- Reduce excessive logging in hot paths

## Best Practices

- Use idempotent task logic (safe retries)
- Give tasks unique, meaningful `name`s and `tags`
- Start the scheduler after application dependencies are ready
- Always stop the scheduler gracefully during shutdown
- Keep task modules modular and avoid circular imports

## Troubleshooting

- Tasks registered twice: ensure discovery or manual registration runs once
- Redis connections exhausted: increase `max_connections` or share pools
- Scheduler appears stuck: check backend availability and task blocking
- Signals not working: verify you're on a supported platform and recent version

## Upgrade Notes

- Project renamed: `chronflow` → `symphra-scheduler`
- Python package: `symphra_scheduler`
- Documentation paths updated to `docs/en` and `docs/zh`

## Related Docs and Examples

- See [Quickstart](../quickstart.md) for installation and first steps
- Check [Monitoring](monitoring.md) and [Logging](logging.md)
- Explore [Backends](backends.md) for Memory/SQLite/Redis/RabbitMQ
- Browse runnable [examples](https://github.com/getaix/symphra-scheduler/tree/main/examples/)