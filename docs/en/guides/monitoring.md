# Monitoring and Stats

Symphra Scheduler provides rich monitoring capabilities to help you understand the state of the scheduler and tasks.

## Get Scheduler Stats

```python
from symphra_scheduler import Scheduler

scheduler = Scheduler()

# Get scheduler stats
stats = await scheduler.get_stats()
print(stats)
```

Sample output:

```python
{
    "running": True,
    "total_tasks": 10,
    "queue_size": 5,
    "active_workers": 8,
    "max_workers": 10,
    "backend": "MemoryBackend",
    "tasks": [
        {
            "name": "health_check",
            "status": "running",
            "metrics": {
                "total_runs": 120,
                "successful_runs": 118,
                "failed_runs": 2,
                "total_execution_time": 60.0,
                "average_execution_time": 0.5,
                "last_run_time": 0.48,
                "last_success_time": 0.48,
                "last_failure_time": null,
                "consecutive_failures": 0
            }
        }
        # ... more tasks
    ]
}
```

## Task List

Get all registered tasks:

```python
tasks = scheduler.list_tasks()

for task in tasks:
    print(f"Task: {task['name']}")
    print(f"Status: {task['status']}")
    print(f"Success rate: {task['success_rate']:.1f}%")
    print(f"Average duration: {task['average_execution_time']:.2f}s")
    print("---")
```

## Task Counts

Count tasks by status:

```python
counts = scheduler.get_task_count()
print(counts)
```

Output:

```python
{
    "total": 10,
    "pending": 2,
    "running": 3,
    "completed": 4,
    "failed": 1,
    "cancelled": 0
}
```

## Get a Single Task

```python
# Get by name
task = scheduler.get_task("health_check")

if task:
    print(f"Task name: {task.config.name}")
    print(f"Current status: {task.status}")
    print(f"Total runs: {task.metrics.total_runs}")
    print(f"Successful runs: {task.metrics.successful_runs}")
    print(f"Failed runs: {task.metrics.failed_runs}")
    print(f"Average duration: {task.metrics.average_execution_time:.2f}s")
```

## Filter by Status

```python
from symphra_scheduler import TaskStatus

# Get failed tasks
failed_tasks = scheduler.get_task_by_status(TaskStatus.FAILED)

for task in failed_tasks:
    print(f"Failed task: {task.config.name}")
    print(f"Consecutive failures: {task.metrics.consecutive_failures}")
    print(f"Last failure time: {task.metrics.last_failure_time}")
```

## Filter by Tag

```python
# Define tasks with tags
@interval(60, tags=["critical", "monitoring"])
async def critical_task():
    pass

@interval(120, tags=["maintenance"])
async def cleanup_task():
    pass

# Get tasks with tag "critical"
critical_tasks = scheduler.get_task_by_tag("critical")

for task in critical_tasks:
    print(f"Critical task: {task.config.name}")
```

## Task Control

### Pause a task

```python
# Pause a task (disable scheduling)
success = await scheduler.pause_task("health_check")

if success:
    print("Task paused")
```

### Resume a task

```python
# Resume a task (enable scheduling)
success = await scheduler.resume_task("health_check")

if success:
    print("Task resumed")
```

## Real-time Monitoring Example

Create a monitoring dashboard:

```python
import asyncio
from symphra_scheduler import Scheduler, interval

scheduler = Scheduler()

@interval(5)  # Monitor every 5 seconds
async def monitor_dashboard():
    """Monitoring dashboard task."""
    stats = await scheduler.get_stats()
    counts = scheduler.get_task_count()

    print("\n" + "="*50)
    print(f"Scheduler: {'running' if stats['running'] else 'stopped'}")
    print(f"Queue size: {stats['queue_size']}")
    print(f"Active workers: {stats['active_workers']}/{stats['max_workers']}")
    print(f"\nTasks:")
    print(f"  Total: {counts['total']}")
    print(f"  Running: {counts['running']}")
    print(f"  Completed: {counts['completed']}")
    print(f"  Failed: {counts['failed']}")

    # Show failed task details
    from symphra_scheduler import TaskStatus
    failed = scheduler.get_task_by_status(TaskStatus.FAILED)
    if failed:
        print(f"\nFailed tasks:")
        for task in failed:
            print(f"  - {task.config.name}: {task.metrics.consecutive_failures} consecutive failures")
    print("="*50)

async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## Task Metrics Explained

### TaskMetrics fields

Each task has a `TaskMetrics` object containing:

- `total_runs`: Total run count
- `successful_runs`: Successful runs
- `failed_runs`: Failed runs
- `total_execution_time`: Total execution time (seconds)
- `average_execution_time`: Average execution time (seconds)
- `last_run_time`: Last run duration (seconds)
- `last_success_time`: Last successful run duration (seconds)
- `last_failure_time`: Last failed run duration (seconds)
- `consecutive_failures`: Consecutive failure count

```python
task = scheduler.get_task("my_task")
metrics = task.metrics

# Compute success rate
success_rate = (metrics.successful_runs / metrics.total_runs * 100
                if metrics.total_runs > 0 else 0.0)

print(f"Success rate: {success_rate:.1f}%")
print(f"Average duration: {metrics.average_execution_time:.2f}s")
print(f"Consecutive failures: {metrics.consecutive_failures}")
```

## Integrate with Monitoring Systems

### Prometheus integration example

```python
from prometheus_client import Gauge, Counter, Histogram
from symphra_scheduler import Scheduler, interval

# Define Prometheus metrics
task_total = Counter('symphra_scheduler_task_total', 'Total tasks', ['task_name'])
task_success = Counter('symphra_scheduler_task_success', 'Successful tasks', ['task_name'])
task_failure = Counter('symphra_scheduler_task_failure', 'Failed tasks', ['task_name'])
task_duration = Histogram('symphra_scheduler_task_duration_seconds', 'Task duration', ['task_name'])

scheduler = Scheduler()

@interval(30)  # Update every 30 seconds
async def update_metrics():
    """Update Prometheus metrics."""
    tasks = scheduler.list_tasks()

    for task_info in tasks:
        task = scheduler.get_task(task_info['name'])
        metrics = task.metrics

        task_total.labels(task_name=task.config.name).inc(metrics.total_runs)
        task_success.labels(task_name=task.config.name).inc(metrics.successful_runs)
        task_failure.labels(task_name=task.config.name).inc(metrics.failed_runs)

        if metrics.last_run_time:
            task_duration.labels(task_name=task.config.name).observe(metrics.last_run_time)
```

## Alerts Configuration

Set up alerts based on metrics:

```python
from symphra_scheduler import Scheduler, interval, TaskStatus

scheduler = Scheduler()

@interval(60)  # Check every minute
async def check_alerts():
    """Check alert conditions."""
    tasks = scheduler.list_tasks()

    for task_info in tasks:
        task = scheduler.get_task(task_info['name'])
        metrics = task.metrics

        # Alert 1: Consecutive failures >= 3
        if metrics.consecutive_failures >= 3:
            await send_alert(
                f"Task {task.config.name} consecutive failures: {metrics.consecutive_failures}"
            )

        # Alert 2: Average duration exceeds threshold
        if metrics.average_execution_time > 30.0:
            await send_alert(
                f"Task {task.config.name} is slow: {metrics.average_execution_time:.2f}s"
            )

        # Alert 3: Success rate below 90%
        if metrics.total_runs > 10:
            success_rate = metrics.successful_runs / metrics.total_runs
            if success_rate < 0.9:
                await send_alert(
                    f"Task {task.config.name} low success rate: {success_rate*100:.1f}%"
                )

async def send_alert(message: str):
    """Send alert (example)."""
    print(f"⚠️  Alert: {message}")
    # In real scenarios, send email/SMS/Slack/Dingtalk, etc.
