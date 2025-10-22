# 性能监控和指标导出

chronflow 提供了内置的性能指标收集功能,可以帮助你监控任务执行情况,分析性能瓶颈,并与 Prometheus 等监控系统集成。

## 快速开始

### 启用指标收集

在创建调度器时,设置 `enable_metrics=True` 即可启用指标收集:

```python
from chronflow import Scheduler

# 创建启用指标的调度器
scheduler = Scheduler(enable_metrics=True)
```

### 获取性能指标

```python
# 获取性能指标
metrics = scheduler.get_metrics()

print(f"总执行次数: {metrics['total_executions']}")
print(f"成功率: {metrics['success_rate']:.2%}")
print(f"平均执行时间: {metrics['average_duration']:.3f}秒")
```

## 指标说明

### 全局指标

`get_metrics()` 返回的字典包含以下全局指标:

- `uptime_seconds`: 调度器运行时长(秒)
- `total_executions`: 总执行次数
- `successful_executions`: 成功执行次数
- `failed_executions`: 失败执行次数
- `success_rate`: 成功率 (0.0 ~ 1.0)
- `total_duration`: 总执行时间(秒)
- `average_duration`: 平均执行时间(秒)
- `executions_per_second`: 每秒执行次数

### 任务级别指标

每个任务都有独立的统计信息:

```python
metrics = scheduler.get_metrics()

for task_name, stats in metrics["task_stats"].items():
    print(f"任务: {task_name}")
    print(f"  执行次数: {stats['executions']}")
    print(f"  成功次数: {stats['successes']}")
    print(f"  失败次数: {stats['failures']}")
    print(f"  成功率: {stats['success_rate']:.2%}")
    print(f"  平均时长: {stats['average_duration']:.3f}秒")
    print(f"  最小时长: {stats['min_duration']:.3f}秒")
    print(f"  最大时长: {stats['max_duration']:.3f}秒")
```

## Prometheus 集成

### 导出 Prometheus 格式

chronflow 支持导出标准的 Prometheus 文本格式:

```python
# 导出 Prometheus 格式的指标
prometheus_text = scheduler.export_prometheus_metrics()
print(prometheus_text)
```

输出示例:

```
# HELP chronflow_uptime_seconds Uptime in seconds
# TYPE chronflow_uptime_seconds gauge
chronflow_uptime_seconds 125.5

# HELP chronflow_executions_total Total task executions
# TYPE chronflow_executions_total counter
chronflow_executions_total 150

# HELP chronflow_executions_success Successful executions
# TYPE chronflow_executions_success counter
chronflow_executions_success 145

# HELP chronflow_executions_failed Failed executions
# TYPE chronflow_executions_failed counter
chronflow_executions_failed 5

# HELP chronflow_task_executions Task executions by name
# TYPE chronflow_task_executions counter
chronflow_task_executions{task="my_task"} 75

# HELP chronflow_task_duration_seconds Task duration by name
# TYPE chronflow_task_duration_seconds gauge
chronflow_task_duration_seconds{task="my_task",stat="avg"} 0.523
chronflow_task_duration_seconds{task="my_task",stat="min"} 0.105
chronflow_task_duration_seconds{task="my_task",stat="max"} 1.250
```

### 创建 HTTP 端点

使用 `aiohttp` 创建 Prometheus 抓取端点:

```python
from aiohttp import web
from chronflow import Scheduler

scheduler = Scheduler(enable_metrics=True)

# 定义指标端点
async def metrics_handler(request):
    """返回 Prometheus 格式的指标。"""
    metrics_text = scheduler.export_prometheus_metrics()
    return web.Response(text=metrics_text or "", content_type="text/plain")

# 创建 web 应用
app = web.Application()
app.router.add_get("/metrics", metrics_handler)

# 启动服务器
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, "localhost", 9090)
await site.start()

print("Prometheus 端点: http://localhost:9090/metrics")
```

### 配置 Prometheus 抓取

在 `prometheus.yml` 中添加抓取配置:

```yaml
scrape_configs:
  - job_name: 'chronflow'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
```

## 指标管理

### 重置指标

在某些场景下,你可能需要重置指标(例如测试或定期清理):

```python
# 重置所有指标
scheduler.reset_metrics()
```

重置后,所有计数器和统计信息将归零,开始时间会更新为当前时间。

### 检查是否启用

```python
if scheduler.metrics_collector is not None:
    print("指标收集已启用")
    metrics = scheduler.get_metrics()
else:
    print("指标收集未启用")
```

## 性能考虑

### 开销

指标收集的性能开销非常小:

- 每次任务执行增加约 0.1-0.5 微秒开销
- 内存开销:每个任务约 200 字节(用于统计信息)
- 对于大多数应用,开销可以忽略不计

### 最佳实践

1. **生产环境建议启用**: 指标对于监控和故障排查非常有价值
2. **定期导出**: 将指标数据导出到监控系统,避免内存积累
3. **关注关键指标**: 重点关注成功率、平均执行时间、失败次数
4. **设置告警**: 基于指标设置告警规则(如失败率超过阈值)

## 完整示例

```python
import asyncio
from chronflow import Scheduler
from chronflow.decorators import interval

async def main():
    # 创建启用指标的调度器
    scheduler = Scheduler(enable_metrics=True)

    # 定义任务
    @interval(seconds=5)
    async def health_check():
        """健康检查任务。"""
        await asyncio.sleep(0.1)
        return "healthy"

    @interval(seconds=10)
    async def data_sync():
        """数据同步任务。"""
        await asyncio.sleep(1.5)
        return "synced"

    # 注册任务
    scheduler.register_task(health_check.__chronflow_task__)
    scheduler.register_task(data_sync.__chronflow_task__)

    # 运行调度器
    async with scheduler.run_context():
        # 定期打印指标
        for _ in range(6):  # 运行 1 分钟
            await asyncio.sleep(10)

            metrics = scheduler.get_metrics()
            print(f"\n=== 性能报告 ({metrics['uptime_seconds']:.0f}秒) ===")
            print(f"总执行: {metrics['total_executions']}")
            print(f"成功率: {metrics['success_rate']:.1%}")
            print(f"平均时长: {metrics['average_duration']:.3f}秒")

            # 导出 Prometheus 指标
            prometheus_text = scheduler.export_prometheus_metrics()
            # 发送到监控系统...

if __name__ == "__main__":
    asyncio.run(main())
```

## 与其他监控系统集成

### StatsD

虽然目前只内置了 Prometheus 格式导出,但你可以轻松地将指标发送到 StatsD:

```python
import aiostatsysd

async def send_to_statsd(scheduler):
    """发送指标到 StatsD。"""
    client = aiostatsysd.Client("localhost", 8125)

    metrics = scheduler.get_metrics()

    # 发送计数器
    await client.counter("chronflow.executions.total", metrics["total_executions"])
    await client.counter("chronflow.executions.success", metrics["successful_executions"])
    await client.counter("chronflow.executions.failed", metrics["failed_executions"])

    # 发送 gauge
    await client.gauge("chronflow.duration.avg", metrics["average_duration"])
    await client.gauge("chronflow.success_rate", metrics["success_rate"] * 100)

    await client.close()
```

### 自定义导出

你也可以实现自己的指标导出器:

```python
class CustomMetricsExporter:
    """自定义指标导出器。"""

    def __init__(self, scheduler):
        self.scheduler = scheduler

    def export_json(self):
        """导出 JSON 格式。"""
        import json
        metrics = self.scheduler.get_metrics()
        return json.dumps(metrics, indent=2)

    def export_influxdb_line_protocol(self):
        """导出 InfluxDB 行协议格式。"""
        metrics = self.scheduler.get_metrics()
        lines = [
            f"chronflow,host=localhost executions={metrics['total_executions']}",
            f"chronflow,host=localhost success_rate={metrics['success_rate']}",
            f"chronflow,host=localhost avg_duration={metrics['average_duration']}",
        ]
        return "\n".join(lines)

# 使用
exporter = CustomMetricsExporter(scheduler)
json_metrics = exporter.export_json()
print(json_metrics)
```

## 下一步

- 查看 [示例代码](../../../examples/metrics_example.py)
- 了解 [日志系统](logging.md)
- 了解 [监控与统计](monitoring.md)
