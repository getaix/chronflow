# 监控与统计

chronflow 提供了丰富的监控功能，帮助你了解调度器和任务的运行状态。

## 获取调度器统计信息

```python
from chronflow import Scheduler

scheduler = Scheduler()

# 获取调度器统计
stats = await scheduler.get_stats()
print(stats)
```

输出示例：

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
            "total_runs": 120,
            "successful_runs": 118,
            "failed_runs": 2,
            "success_rate": 98.3,
            "avg_execution_time": 0.5
        },
        # ... 更多任务
    ]
}
```

## 任务列表

获取所有已注册的任务：

```python
tasks = scheduler.list_tasks()

for task in tasks:
    print(f"任务: {task['name']}")
    print(f"状态: {task['status']}")
    print(f"成功率: {task['success_rate']:.1f}%")
    print(f"平均执行时间: {task['avg_execution_time']:.2f}s")
    print("---")
```

## 任务计数

按状态统计任务数量：

```python
counts = scheduler.get_task_count()
print(counts)
```

输出：

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

## 获取单个任务

```python
# 按名称获取任务
task = scheduler.get_task("health_check")

if task:
    print(f"任务名称: {task.config.name}")
    print(f"当前状态: {task.status}")
    print(f"总运行次数: {task.metrics.total_runs}")
    print(f"成功次数: {task.metrics.successful_runs}")
    print(f"失败次数: {task.metrics.failed_runs}")
    print(f"平均执行时间: {task.metrics.average_execution_time:.2f}s")
```

## 按状态筛选任务

```python
from chronflow import TaskStatus

# 获取失败的任务
failed_tasks = scheduler.get_task_by_status(TaskStatus.FAILED)

for task in failed_tasks:
    print(f"失败任务: {task.config.name}")
    print(f"连续失败次数: {task.metrics.consecutive_failures}")
    print(f"最后失败时间: {task.metrics.last_failure_time}")
```

## 按标签筛选任务

```python
# 定义带标签的任务
@interval(60, tags=["critical", "monitoring"])
async def critical_task():
    pass

@interval(120, tags=["maintenance"])
async def cleanup_task():
    pass

# 获取带 "critical" 标签的任务
critical_tasks = scheduler.get_task_by_tag("critical")

for task in critical_tasks:
    print(f"关键任务: {task.config.name}")
```

## 任务控制

### 暂停任务

```python
# 暂停任务（禁用调度）
success = await scheduler.pause_task("health_check")

if success:
    print("任务已暂停")
```

### 恢复任务

```python
# 恢复任务（启用调度）
success = await scheduler.resume_task("health_check")

if success:
    print("任务已恢复")
```

## 实时监控示例

创建一个监控仪表板：

```python
import asyncio
from chronflow import Scheduler, interval

scheduler = Scheduler()

@interval(5)  # 每5秒监控一次
async def monitor_dashboard():
    """监控仪表板任务。"""
    stats = await scheduler.get_stats()
    counts = scheduler.get_task_count()

    print("\n" + "="*50)
    print(f"调度器状态: {'运行中' if stats['running'] else '已停止'}")
    print(f"队列大小: {stats['queue_size']}")
    print(f"活跃工作协程: {stats['active_workers']}/{stats['max_workers']}")
    print(f"\n任务统计:")
    print(f"  总计: {counts['total']}")
    print(f"  运行中: {counts['running']}")
    print(f"  已完成: {counts['completed']}")
    print(f"  失败: {counts['failed']}")

    # 显示失败任务详情
    from chronflow import TaskStatus
    failed = scheduler.get_task_by_status(TaskStatus.FAILED)
    if failed:
        print(f"\n失败任务:")
        for task in failed:
            print(f"  - {task.config.name}: {task.metrics.consecutive_failures} 次连续失败")
    print("="*50)

async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 任务指标详解

### TaskMetrics 指标说明

每个任务都有一个 `TaskMetrics` 对象，包含以下指标：

- `total_runs`: 总运行次数
- `successful_runs`: 成功次数
- `failed_runs`: 失败次数
- `total_execution_time`: 总执行时间（秒）
- `average_execution_time`: 平均执行时间（秒）
- `last_run_time`: 最后一次运行时间（秒）
- `last_success_time`: 最后一次成功时间（秒）
- `last_failure_time`: 最后一次失败时间（秒）
- `consecutive_failures`: 连续失败次数
- `last_error`: 最后一次错误信息

```python
task = scheduler.get_task("my_task")
metrics = task.metrics

# 计算成功率
success_rate = (metrics.successful_runs / metrics.total_runs * 100
                if metrics.total_runs > 0 else 0.0)

print(f"成功率: {success_rate:.1f}%")
print(f"平均执行时间: {metrics.average_execution_time:.2f}s")
print(f"连续失败: {metrics.consecutive_failures} 次")
```

## 集成到监控系统

### Prometheus 集成示例

```python
from prometheus_client import Gauge, Counter, Histogram
from chronflow import Scheduler, interval

# 定义 Prometheus 指标
task_total = Counter('chronflow_task_total', 'Total tasks', ['task_name'])
task_success = Counter('chronflow_task_success', 'Successful tasks', ['task_name'])
task_failure = Counter('chronflow_task_failure', 'Failed tasks', ['task_name'])
task_duration = Histogram('chronflow_task_duration_seconds', 'Task duration', ['task_name'])

scheduler = Scheduler()

@interval(30)  # 每30秒更新指标
async def update_metrics():
    """更新 Prometheus 指标。"""
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

## 告警配置

基于指标设置告警：

```python
from chronflow import Scheduler, interval, TaskStatus

scheduler = Scheduler()

@interval(60)  # 每分钟检查一次
async def check_alerts():
    """检查告警条件。"""
    tasks = scheduler.list_tasks()

    for task_info in tasks:
        task = scheduler.get_task(task_info['name'])
        metrics = task.metrics

        # 告警条件1: 连续失败超过3次
        if metrics.consecutive_failures >= 3:
            await send_alert(
                f"任务 {task.config.name} 连续失败 {metrics.consecutive_failures} 次"
            )

        # 告警条件2: 平均执行时间超过阈值
        if metrics.average_execution_time > 30.0:
            await send_alert(
                f"任务 {task.config.name} 执行时间过长: {metrics.average_execution_time:.2f}s"
            )

        # 告警条件3: 成功率低于90%
        if metrics.total_runs > 10:
            success_rate = metrics.successful_runs / metrics.total_runs
            if success_rate < 0.9:
                await send_alert(
                    f"任务 {task.config.name} 成功率过低: {success_rate*100:.1f}%"
                )

async def send_alert(message: str):
    """发送告警（示例）。"""
    print(f"⚠️  告警: {message}")
    # 实际场景可以发送邮件、短信、钉钉消息等
```
