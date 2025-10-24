# Chronflow 集成指南

本指南帮助你正确集成 Chronflow,避免常见的陷阱和问题。

## 常见问题及解决方案

### 1. 任务重复执行

**问题:** 同一个任务被多个 worker 同时执行

**原因:** 任务装饰器被多次调用,导致重复注册

**解决方案:**

```python
# ✅ 正确: 装饰器在模块顶层使用
from chronflow import interval

@interval(seconds=10, name="my_task")
async def my_task():
    """每10秒执行一次"""
    print("执行任务...")

# ❌ 错误: 在函数中动态注册
def init_tasks():
    @interval(seconds=10)  # 每次调用都会重新注册
    async def my_task():
        print("执行任务...")
```

**检查清单:**
- ✅ 装饰器在模块顶层使用(import时执行一次)
- ✅ 不要在函数/方法中动态调用装饰器
- ✅ 确保模块不会被重复导入
- ✅ 使用 `name` 参数为任务指定唯一名称

### 2. Ctrl+C 无法停止

**问题:** 前台运行时按 Ctrl+C 无法停止调度器

**原因:** 旧版本未在非守护模式注册信号处理器

**解决方案:** 升级到 v0.2.1 或更高版本

```bash
pip install --upgrade chronflow
```

该版本已自动注册 SIGINT 和 SIGTERM 信号处理器。

### 3. 守护进程输出到终端

**问题:** 后台运行时日志仍然输出到终端

**原因:** 旧版本未重定向标准输入/输出/错误

**解决方案:** 升级到 v0.2.1 或更高版本

```bash
pip install --upgrade chronflow
```

或手动重定向输出:
```bash
python your_script.py > /dev/null 2>&1 &
```

### 4. Redis 连接数过多

**问题:** `redis.exceptions.ConnectionError: Too many connections`

**原因:**
- 任务重复注册导致连接数激增
- 连接池配置过小

**解决方案:**

```python
from chronflow import Scheduler, SchedulerConfig

# 增加连接池大小
config = SchedulerConfig(
    backend_type="redis",
    redis={"max_connections": 50},  # 增加连接池
    max_workers=5,  # 减少 worker 数量
)

scheduler = Scheduler(config)
```

## 正确的集成方式

### 方式 A: 嵌入异步应用 (FastAPI, Quart, Sanic 等)

```python
import asyncio
from chronflow import Scheduler, interval

# 定义任务
@interval(seconds=30)
async def health_check():
    """健康检查任务"""
    print("执行健康检查...")

# 应用生命周期管理
class Application:
    def __init__(self):
        self.scheduler = Scheduler()

    async def startup(self):
        """应用启动"""
        # 作为后台任务启动调度器(不阻塞)
        asyncio.create_task(self.scheduler.start())
        print("调度器已启动")

    async def shutdown(self):
        """应用关闭"""
        await self.scheduler.stop()
        print("调度器已停止")
```

### 方式 B: 独立守护进程

```python
# scheduler_daemon.py
import asyncio
from chronflow import Scheduler, interval

@interval(seconds=60)
async def cleanup_task():
    """定期清理任务"""
    print("执行清理...")

async def main():
    """启动调度器守护进程"""
    scheduler = Scheduler()

    # 以守护进程模式启动
    pid = await scheduler.start(daemon=True)
    print(f"调度器守护进程已启动,PID: {pid}")

if __name__ == "__main__":
    asyncio.run(main())
```

运行:
```bash
python scheduler_daemon.py
```

停止:
```bash
# 发送 SIGTERM 信号
kill -TERM <pid>
```

### 方式 C: 前台运行 (开发环境)

```python
# scheduler_foreground.py
import asyncio
from chronflow import Scheduler, cron

@cron("*/5 * * * * *")  # 每5秒
async def log_task():
    """日志任务"""
    print("记录日志...")

async def main():
    """前台运行调度器"""
    scheduler = Scheduler()

    # 前台运行(阻塞,可通过 Ctrl+C 停止)
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

运行:
```bash
python scheduler_foreground.py
# 按 Ctrl+C 优雅停止
```

## 配置管理

### 使用配置对象

```python
from chronflow import Scheduler, SchedulerConfig

config = SchedulerConfig(
    backend_type="redis",
    max_workers=10,
    queue_size=1000,
    timezone="Asia/Shanghai",
    redis={
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "max_connections": 50,
    },
)

scheduler = Scheduler(config)
```

### 使用配置文件

```yaml
# config.yaml
scheduler:
  backend_type: redis
  max_workers: 10
  queue_size: 1000
  timezone: Asia/Shanghai
  redis:
    host: localhost
    port: 6379
    db: 0
    max_connections: 50
```

```python
from chronflow import Scheduler, SchedulerConfig

# 从文件加载配置
config = SchedulerConfig.from_yaml("config.yaml")
scheduler = Scheduler(config)
```

### 使用环境变量

```bash
export SCHEDULER__BACKEND_TYPE=redis
export SCHEDULER__MAX_WORKERS=10
export SCHEDULER__REDIS__HOST=localhost
export SCHEDULER__REDIS__PORT=6379
```

```python
from chronflow import Scheduler, SchedulerConfig

# 从环境变量加载
config = SchedulerConfig()
scheduler = Scheduler(config)
```

## 监控和调试

### 查看调度器状态

```python
async def monitor_scheduler(scheduler: Scheduler):
    """监控调度器状态"""
    stats = await scheduler.get_stats()
    print(f"运行状态: {stats['running']}")
    print(f"总任务数: {stats['total_tasks']}")
    print(f"队列大小: {stats['queue_size']}")
    print(f"活跃 workers: {stats['active_workers']}")
```

### 查看任务列表

```python
def list_tasks(scheduler: Scheduler):
    """列出所有任务及其状态"""
    tasks = scheduler.list_tasks()
    for task in tasks:
        print(f"{task['name']}")
        print(f"  状态: {task['status']}")
        print(f"  总执行: {task['total_runs']}")
        print(f"  成功: {task['successful_runs']}")
        print(f"  失败: {task['failed_runs']}")
        print(f"  成功率: {task['success_rate']:.1f}%")
```

### 任务控制

```python
# 暂停任务
scheduler.pause_task("my_task")

# 恢复任务
scheduler.resume_task("my_task")

# 按状态筛选
active_tasks = scheduler.get_task_by_status("running")

# 按标签筛选
tagged_tasks = scheduler.get_task_by_tag("important")
```

## 日志配置

### 使用 Structlog

```python
from chronflow import Scheduler, StructlogAdapter

scheduler = Scheduler(logger=StructlogAdapter())
```

### 使用 Loguru

```python
from chronflow import Scheduler, LoguruAdapter
from loguru import logger

# 配置日志输出到文件
logger.add("scheduler.log", rotation="1 day", retention="7 days")

scheduler = Scheduler(logger=LoguruAdapter())
```

### 使用 Python 标准库 logging

```python
import logging
from chronflow import Scheduler, StdlibAdapter

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler(),
    ]
)

scheduler = Scheduler(logger=StdlibAdapter())
```

### 禁用日志

```python
from chronflow import Scheduler, NoOpAdapter

scheduler = Scheduler(logger=NoOpAdapter())
```

## 性能优化

### 1. 合理配置 Worker 数量

```python
# CPU 密集型任务
config = SchedulerConfig(max_workers=cpu_count())

# I/O 密集型任务
config = SchedulerConfig(max_workers=cpu_count() * 2)
```

### 2. 选择合适的后端

- **Memory**: 零依赖,适合轻量级应用
- **SQLite**: 本地持久化,适合单机部署
- **Redis**: 分布式部署,适合高性能场景
- **RabbitMQ**: 高可靠性,适合关键任务

### 3. 调整队列大小

```python
# 任务量大时增加队列大小
config = SchedulerConfig(queue_size=5000)
```

### 4. 减少日志量

```python
config = SchedulerConfig(
    enable_logging=True,
    log_task_success=False,  # 不记录成功任务
)
```

## 最佳实践

1. **环境隔离:** 开发环境使用前台模式,生产环境使用守护进程
2. **资源限制:** 根据任务负载调整 `max_workers` 和连接池大小
3. **错误处理:** 在任务函数中添加异常处理和重试逻辑
4. **日志配置:** 配置日志文件输出,方便问题排查
5. **监控告警:** 定期检查调度器状态和任务执行情况
6. **优雅停止:** 使用信号处理或 `stop()` 方法正确停止调度器

## 故障排查

### 检查任务是否重复注册

```python
from chronflow.decorators import _pending_tasks

# 检查待注册任务
print([t.config.name for t in _pending_tasks])

# 检查已注册任务
tasks = scheduler.list_tasks()
print([t['name'] for t in tasks])
```

### 检查 Redis 连接数

```bash
# 查看当前连接数
redis-cli CLIENT LIST | wc -l

# 查看最大连接数
redis-cli CONFIG GET maxclients
```

### 查看进程状态

```bash
# 查看调度器进程
ps aux | grep python | grep scheduler

# 查看进程 CPU/内存占用
top -p <pid>
```

## 升级到 v0.2.1

从旧版本升级时,需要注意:

1. **无破坏性变更** - 完全向后兼容
2. **自动修复** - 信号处理和日志错误已自动修复
3. **测试验证** - 升级后运行测试确保正常

```bash
# 升级 Chronflow
pip install --upgrade chronflow

# 运行测试
pytest tests/
```

---

更多详情请参考:
- [更新日志](../changelog.md#021-2025-10-24)
- [API 文档](../api/scheduler.md)
- [快速开始](../quickstart.md)
