# Performance Monitoring and Metrics Export

Symphra Scheduler provides built-in performance metrics that help you monitor task execution, analyze bottlenecks, and integrate with Prometheus.

## Quick Start

### Enable metrics collection

Enable metrics when creating the scheduler by setting `enable_metrics=True`:

```python
from symphra_scheduler import Scheduler

# Create a scheduler with metrics enabled
scheduler = Scheduler(enable_metrics=True)
```

### Get performance metrics

```python
# Get performance metrics
metrics = scheduler.get_metrics()

print(f"Total executions: {metrics['total_executions']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Average duration: {metrics['average_duration']:.3f}s")
```

## Metrics Overview

### Global metrics

`get_metrics()` returns a dictionary with the following global metrics:

- `uptime_seconds`: Scheduler uptime in seconds
- `total_executions`: Total number of task executions
- `successful_executions`: Successful executions
- `failed_executions`: Failed executions
- `success_rate`: Success rate (0.0 ~ 1.0)
- `total_duration`: Total execution time in seconds
- `average_duration`: Average execution time in seconds
- `executions_per_second`: Executions per second

### Per-task metrics

Each task has independent statistics:

```python
metrics = scheduler.get_metrics()

for task_name, stats in metrics["task_stats"].items():
    print(f"Task: {task_name}")
    print(f"  Executions: {stats['executions']}")
    print(f"  Successes: {stats['successes']}")
    print(f"  Failures: {stats['failures']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    print(f"  Average duration: {stats['average_duration']:.3f}s")
    print(f"  Min duration: {stats['min_duration']:.3f}s")
    print(f"  Max duration: {stats['max_duration']:.3f}s")
```

## Prometheus Integration

### Export Prometheus format

Symphra Scheduler can export standard Prometheus text format:

```python
# Export metrics in Prometheus format
prometheus_text = scheduler.export_prometheus_metrics()
print(prometheus_text)
```

Sample output:

```
# HELP symphra_scheduler_uptime_seconds Uptime in seconds
# TYPE symphra_scheduler_uptime_seconds gauge
symphra_scheduler_uptime_seconds 125.5

# HELP symphra_scheduler_executions_total Total task executions
# TYPE symphra_scheduler_executions_total counter
symphra_scheduler_executions_total 150

# HELP symphra_scheduler_executions_success Successful executions
# TYPE symphra_scheduler_executions_success counter
symphra_scheduler_executions_success 145

# HELP symphra_scheduler_executions_failed Failed executions
# TYPE symphra_scheduler_executions_failed counter
symphra_scheduler_executions_failed 5

# HELP symphra_scheduler_task_executions Task executions by name
# TYPE symphra_scheduler_task_executions counter
symphra_scheduler_task_executions{task="my_task"} 75

# HELP symphra_scheduler_task_duration_seconds Task duration by name
# TYPE symphra_scheduler_task_duration_seconds gauge
symphra_scheduler_task_duration_seconds{task="my_task",stat="avg"} 0.523
symphra_scheduler_task_duration_seconds{task="my_task",stat="min"} 0.105
symphra_scheduler_task_duration_seconds{task="my_task",stat="max"} 1.250
```

### Create an HTTP endpoint

Use `aiohttp` to serve a Prometheus scrape endpoint:

```python
from aiohttp import web
from symphra_scheduler import Scheduler

scheduler = Scheduler(enable_metrics=True)

# Metrics endpoint
async def metrics_handler(request):
    """Return metrics in Prometheus text format."""
    metrics_text = scheduler.export_prometheus_metrics()
    return web.Response(text=metrics_text or "", content_type="text/plain")

# Create web app
app = web.Application()
app.router.add_get("/metrics", metrics_handler)

# Start server
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, "localhost", 9090)
await site.start()

print("Prometheus endpoint: http://localhost:9090/metrics")
```

### Configure Prometheus scrape

Add the following to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'symphra_scheduler'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
```

## Metrics Management

### Reset metrics

In some cases you may want to reset metrics (e.g., tests or periodic cleanup):

```python
# Reset all metrics
scheduler.reset_metrics()
```

After reset, all counters and stats are zeroed, and the start time is updated.

### Check if enabled

```python
if scheduler.metrics_collector is not None:
    print("Metrics collection is enabled")
    metrics = scheduler.get_metrics()
else:
    print("Metrics collection is disabled")
```

## Performance Considerations

### Overhead

Metrics collection overhead is very small:

- ~0.1–0.5 microseconds per task execution
- Memory: ~200 bytes per task for stats
- Negligible for most applications

### Best practices

1. Enable in production: metrics are invaluable for monitoring and troubleshooting
2. Export regularly: send metrics to your monitoring system to avoid memory buildup
3. Focus on key metrics: success rate, average duration, failure count
4. Set alerts: trigger alerts based on thresholds (e.g., failure rate)

## Complete Example

```python
import asyncio
from symphra_scheduler import Scheduler
from symphra_scheduler.decorators import interval

async def main():
    # Create a scheduler with metrics enabled
    scheduler = Scheduler(enable_metrics=True)

    # Define tasks
    @interval(seconds=5)
    async def health_check():
        """Health check task."""
        await asyncio.sleep(0.1)
        return "healthy"

    @interval(seconds=10)
    async def data_sync():
        """Data sync task."""
        await asyncio.sleep(1.5)
        return "synced"

    # Register tasks
    scheduler.register_task(health_check.__symphra_scheduler_task__)
    scheduler.register_task(data_sync.__symphra_scheduler_task__)

    # Run scheduler
    async with scheduler.run_context():
        # Periodically print metrics
        for _ in range(6):  # Run for 1 minute
            await asyncio.sleep(10)

            metrics = scheduler.get_metrics()
            print(f"\n=== Performance report ({metrics['uptime_seconds']:.0f}s) ===")
            print(f"Total: {metrics['total_executions']}")
            print(f"Success rate: {metrics['success_rate']:.1%}")
            print(f"Average duration: {metrics['average_duration']:.3f}s")

            # Export Prometheus metrics
            prometheus_text = scheduler.export_prometheus_metrics()
            # Send to monitoring system...

if __name__ == "__main__":
    asyncio.run(main())
```

## Integrate with Other Systems

### StatsD

While Prometheus text export is built-in, you can also send metrics to StatsD easily:

```python
import aiostatsysd

async def send_to_statsd(scheduler):
    """Send metrics to StatsD."""
    client = aiostatsysd.Client("localhost", 8125)

    metrics = scheduler.get_metrics()

    # Counters
    await client.counter("symphra_scheduler.executions.total", metrics["total_executions"])
    await client.counter("symphra_scheduler.executions.success", metrics["successful_executions"]) 
    await client.counter("symphra_scheduler.executions.failed", metrics["failed_executions"]) 

    # Gauges
    await client.gauge("symphra_scheduler.duration.avg", metrics["average_duration"]) 
    await client.gauge("symphra_scheduler.success_rate", metrics["success_rate"] * 100) 

    await client.close()
```

### Custom Exporter

You can implement your own metrics exporter:

```python
class CustomMetricsExporter:
    """Custom metrics exporter."""

    def __init__(self, scheduler):
        self.scheduler = scheduler

    def export_json(self):
        """Export JSON format."""
        import json
        metrics = self.scheduler.get_metrics()
        return json.dumps(metrics, indent=2)

    def export_influxdb_line_protocol(self):
        """Export InfluxDB line protocol format."""
        metrics = self.scheduler.get_metrics()
        lines = [
            f"symphra_scheduler,host=localhost executions={metrics['total_executions']}",
            f"symphra_scheduler,host=localhost success_rate={metrics['success_rate']}",
            f"symphra_scheduler,host=localhost avg_duration={metrics['average_duration']}",
        ]
        return "\n".join(lines)

# Usage
exporter = CustomMetricsExporter(scheduler)
json_metrics = exporter.export_json()
print(json_metrics)
```

## Next Steps

- View the [example code](https://github.com/getaix/symphra-scheduler/blob/main/examples/metrics_example.py)
- Learn about [Logging](logging.md)
- Learn about [Monitoring & Stats](monitoring.md)