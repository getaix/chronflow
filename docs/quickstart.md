# chronflow 快速开始指南

## 5 分钟上手

### 1. 安装

使用 uv (推荐):
```bash
uv pip install chronflow
```

使用 pip:
```bash
pip install chronflow
```

### 2. 第一个定时任务

创建 `app.py`:

```python
import asyncio
from chronflow import Scheduler, interval

# 创建调度器
scheduler = Scheduler()

# 定义任务 - 每 5 秒执行一次
@interval(5)
async def hello_task():
    print("Hello, chronflow!")

# 运行调度器
async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

运行:
```bash
python app.py
```

### 3. 使用 Cron 表达式

```python
from chronflow import cron

# 每天上午 9 点执行
@cron("0 0 9 * * *")
async def daily_report():
    print("生成每日报表...")
    # 你的业务逻辑

# 每 5 秒执行
@cron("*/5 * * * * *")
async def health_check():
    print("健康检查...")
```

### 4. 添加重试机制

```python
from chronflow import interval, RetryPolicy

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
    # 这个任务失败后会自动重试最多 5 次
    await do_something_critical()
```

### 5. 使用持久化队列

```python
from chronflow import Scheduler
from chronflow.backends import SQLiteBackend

# 使用 SQLite 持久化
backend = SQLiteBackend(db_path="tasks.db")
scheduler = Scheduler(backend=backend)

# 任务会保存到数据库,重启后不会丢失
@interval(60)
async def persistent_task():
    print("这个任务会被持久化!")
```

### 6. 分布式部署 (Redis)

```bash
# 安装 Redis 支持
uv pip install chronflow[redis]
```

```python
from chronflow import Scheduler, SchedulerConfig
from chronflow.backends import RedisBackend

# 配置 Redis 后端
backend = RedisBackend(url="redis://localhost:6379/0")
config = SchedulerConfig(max_workers=20)

scheduler = Scheduler(config=config, backend=backend)

# 多个实例共享同一个 Redis 队列
@interval(10)
async def distributed_task():
    print("分布式任务执行中...")
```

## 常用场景

### 数据同步

```python
@interval(300)  # 每 5 分钟
async def sync_data():
    """从 API 同步数据"""
    data = await fetch_from_api()
    await save_to_database(data)
```

### 定时清理

```python
@cron("0 0 2 * * *")  # 每天凌晨 2 点
async def cleanup():
    """清理过期数据"""
    await delete_old_records()
```

### 健康监控

```python
@interval(30)
async def monitor_services():
    """监控服务健康状态"""
    for service in services:
        if not await service.is_healthy():
            await send_alert(f"{service.name} 异常!")
```

### 报表生成

```python
@cron("0 0 18 * * 1-5")  # 工作日下午 6 点
async def daily_report():
    """生成每日报表"""
    report = await generate_report()
    await send_email(report)
```

## 配置文件方式

创建 `config.toml`:

```toml
max_workers = 20
queue_size = 5000
log_level = "INFO"
timezone = "Asia/Shanghai"
```

使用配置:

```python
from chronflow import Scheduler, SchedulerConfig

config = SchedulerConfig.from_file("config.toml")
scheduler = Scheduler(config=config)
```

## 监控和调试

```python
# 获取调度器状态
stats = await scheduler.get_stats()
print(f"运行中: {stats['running']}")
print(f"任务数: {stats['total_tasks']}")
print(f"队列大小: {stats['queue_size']}")

# 获取任务指标
task = scheduler.get_task("my_task")
print(f"总运行次数: {task.metrics.total_runs}")
print(f"成功率: {task.metrics.successful_runs / task.metrics.total_runs * 100}%")
```

## 下一步

- 查看 [README.md](README.md) 了解完整功能
- 查看 [examples/](examples/) 目录的示例代码
- 阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何贡献代码

## 常见问题

**Q: 如何优雅地关闭调度器?**

A: 使用 `Ctrl+C` 或调用 `await scheduler.stop()`,调度器会等待所有运行中的任务完成。

**Q: 任务执行失败怎么办?**

A: 配置重试策略,失败的任务会自动重试。查看任务指标了解失败原因。

**Q: 支持分布式部署吗?**

A: 支持!使用 Redis 或 RabbitMQ 后端即可实现多实例部署。

**Q: 性能如何?**

A: 基于原生 asyncio,低延迟高吞吐。内存后端可支持 10000+ 任务/秒。
