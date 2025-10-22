# chronflow

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

高性能异步定时任务调度库,专为 Python 3.11+ 设计。

## 特性

- **高性能异步** - 基于 asyncio,支持高并发任务执行
- **秒级精度** - 支持秒级定时任务,基于 Cron 表达式
- **多种后端** - 支持内存、Redis、RabbitMQ、SQLite 作为队列后端
- **重试机制** - 内置智能重试,支持指数退避策略
- **简洁 API** - 装饰器模式,一行代码即可定义任务
- **类型安全** - 完整的类型提示,IDE 友好
- **配置灵活** - 支持代码配置、文件配置(JSON/TOML/YAML)
- **后台运行** - 支持守护进程模式,优雅关闭
- **低内存占用** - 精心优化,适合长时间运行
- **零依赖启动** - 默认内存后端,无需外部服务

## 安装

### 基础安装(仅内存/SQLite后端)

```bash
pip install chronflow
```

### 安装 Redis 支持

```bash
pip install chronflow[redis]
# 或
pip install chronflow redis
```

### 安装 RabbitMQ 支持

```bash
pip install chronflow[rabbitmq]
# 或
pip install chronflow aio-pika
```

### 完整安装

```bash
pip install chronflow[all]
```

## 快速开始

### 基础用法

```python
import asyncio
from chronflow import Scheduler, cron, interval

# 创建调度器
scheduler = Scheduler()

# 使用装饰器定义任务
@cron("*/5 * * * * *")  # 每5秒执行
async def task1():
    print("每5秒执行一次")

@interval(30)  # 每30秒执行
async def task2():
    print("每30秒执行一次")

# 运行调度器
async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### 使用 Redis 后端

```python
from chronflow import Scheduler, SchedulerConfig, cron
from chronflow.backends import RedisBackend

# 配置 Redis 后端
backend = RedisBackend(url="redis://localhost:6379/0")
config = SchedulerConfig(max_workers=20)

scheduler = Scheduler(config=config, backend=backend)

@cron("0 0 * * *")  # 每天零点执行
async def daily_cleanup():
    print("执行每日清理任务")
    await cleanup_old_data()

async def main():
    await scheduler.start(daemon=True)

asyncio.run(main())
```

### 使用 SQLite 本地持久化

```python
from chronflow import Scheduler, interval
from chronflow.backends import SQLiteBackend

# SQLite 后端,任务持久化到本地文件
backend = SQLiteBackend(db_path="scheduler.db")
scheduler = Scheduler(backend=backend)

@interval(60)
async def sync_task():
    print("同步数据...")
    await sync_data()

asyncio.run(scheduler.start())
```

### 高级用法

```python
from datetime import datetime, timedelta
from chronflow import Scheduler, scheduled, RetryPolicy

scheduler = Scheduler()

# 自定义重试策略
@scheduled(
    interval=10,
    retry_policy=RetryPolicy(
        max_attempts=5,
        strategy="exponential",
        wait_min=1.0,
        wait_max=60.0,
    ),
    timeout=30.0,  # 30秒超时
    max_instances=3,  # 最多3个并发实例
    tags=["critical", "data-sync"],
)
async def important_task():
    """重要任务,需要重试和超时控制"""
    await process_critical_data()

# 一次性任务
from chronflow.decorators import once

@once(at=datetime(2025, 12, 31, 23, 59, 59))
async def new_year_celebration():
    print("新年快乐!")
```

### 配置文件方式

**config.toml:**

```toml
max_workers = 20
queue_size = 5000
shutdown_timeout = 60.0
enable_logging = true
log_level = "INFO"
timezone = "Asia/Shanghai"
persistence_enabled = true
persistence_path = "scheduler_state.json"
```

**Python 代码:**

```python
from chronflow import Scheduler, SchedulerConfig

# 从配置文件加载
config = SchedulerConfig.from_file("config.toml")
scheduler = Scheduler(config=config)
```

## 后端对比

| 后端 | 适用场景 | 持久化 | 分布式 | 性能 | 依赖 |
|------|---------|--------|--------|------|------|
| **Memory** | 开发、测试、单机 | ✗ | ✗ | ⭐⭐⭐⭐⭐ | 无 |
| **SQLite** | 单机生产、需要持久化 | ✓ | ✗ | ⭐⭐⭐⭐ | 无 |
| **Redis** | 分布式、高性能 | ✓ | ✓ | ⭐⭐⭐⭐⭐ | Redis |
| **RabbitMQ** | 高可靠性、消息队列 | ✓ | ✓ | ⭐⭐⭐⭐ | RabbitMQ |

## Cron 表达式

chronflow 支持标准 Cron 表达式,并扩展支持秒级精度:

```
秒 分 时 日 月 周

示例:
*/5 * * * * *       - 每5秒
0 */10 * * * *      - 每10分钟
0 0 9 * * *         - 每天上午9点
0 0 0 1 * *         - 每月1号零点
0 0 0 * * 1         - 每周一零点
*/30 * 9-17 * * 1-5 - 工作日9-17点每30秒
```

## 监控和统计

```python
# 获取调度器统计信息
stats = await scheduler.get_stats()
print(stats)
# {
#     "running": true,
#     "total_tasks": 5,
#     "queue_size": 12,
#     "active_workers": 10,
#     "max_workers": 20,
#     "backend": "RedisBackend",
#     "tasks": [...]
# }

# 获取单个任务的指标
task = scheduler.get_task("task_name")
print(task.metrics)
# TaskMetrics(
#     total_runs=100,
#     successful_runs=95,
#     failed_runs=5,
#     average_execution_time=1.23
# )
```

## 架构设计

```
┌─────────────────────────────────────────┐
│           Scheduler (调度器)             │
│  - 任务注册和管理                         │
│  - 工作协程池                             │
│  - 优雅关闭                               │
└───────────┬─────────────────────────────┘
            │
            ├─── 装饰器 API (@cron, @interval)
            │
            ├─── 任务队列
            │    └─── 后端抽象层
            │         ├─── MemoryBackend
            │         ├─── SQLiteBackend
            │         ├─── RedisBackend
            │         └─── RabbitMQBackend
            │
            └─── 任务执行
                 ├─── 超时控制
                 ├─── 重试机制 (tenacity)
                 ├─── 并发控制
                 └─── 指标收集
```

## 为什么选择 chronflow?

### vs Celery

- ✅ **更轻量** - 无需 Redis/RabbitMQ 即可运行
- ✅ **更简单** - 装饰器即用,无需额外配置
- ✅ **更快速** - 纯 asyncio,无进程开销
- ✅ **更现代** - Python 3.11+ 新特性,完整类型提示

### vs APScheduler

- ✅ **更高性能** - 原生异步,不是同步转异步
- ✅ **更好的可靠性** - 经过优化的内存管理
- ✅ **更灵活** - 可插拔后端,支持多种存储
- ✅ **更好的可观测性** - 内置指标和监控

## 开发

```bash
# 克隆仓库
git clone https://github.com/getaix/chronflow.git
cd chronflow

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v --cov=chronflow --cov-report=html

# 代码检查
ruff check chronflow/
mypy chronflow/

# 格式化代码
black chronflow/
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request!

## 链接

- 📖 [完整文档](https://getaix.github.io/chronflow)
- 🐛 [问题反馈](https://github.com/getaix/chronflow/issues)
- 📦 [PyPI](https://pypi.org/project/chronflow/)
