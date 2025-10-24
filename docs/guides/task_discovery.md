# 任务自动发现

chronflow 提供了强大的任务自动发现机制,可以自动扫描项目目录或包,发现并注册使用装饰器定义的定时任务,极大简化项目集成流程。

## 功能特性

- ✅ **按目录扫描** - 自动扫描指定目录下的 Python 文件
- ✅ **按包导入** - 从已安装的 Python 包中发现任务
- ✅ **自定义模式** - 支持通配符文件名匹配 (`task.py`, `*_tasks.py` 等)
- ✅ **递归扫描** - 支持递归扫描子目录
- ✅ **灵活过滤** - 支持排除特定文件或模式
- ✅ **自动注册** - 发现的任务自动注册到调度器
- ✅ **错误容错** - 导入失败的模块会被跳过,不影响其他任务

## 基础用法

### 从目录发现任务

适合按模块组织的项目结构:

```python
from chronflow import Scheduler

scheduler = Scheduler()

# 扫描目录下所有 task.py 文件
tasks = scheduler.discover_tasks_from_directory("app/modules")

# 发现的任务已自动注册到调度器
print(f"发现 {len(tasks)} 个任务")
```

### 使用自定义文件名模式

```python
# 扫描所有 *_tasks.py 文件
tasks = scheduler.discover_tasks_from_directory(
    "app",
    pattern="*_tasks.py",
    exclude_patterns=["test_*.py", "*_backup.py"]
)
```

### 从包中发现任务

适合从已安装的 Python 包中发现任务:

```python
# 从包及其子包中发现任务
tasks = scheduler.discover_tasks_from_package("my_app.tasks")
```

### 从指定模块列表导入

适合精确控制要加载的模块:

```python
tasks = scheduler.discover_tasks_from_modules([
    "my_app.tasks.user_tasks",
    "my_app.tasks.email_tasks",
    "my_app.tasks.report_tasks",
])
```

## 实际项目示例

### 项目结构

```
my_project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── modules/
│       ├── __init__.py
│       ├── user/
│       │   ├── __init__.py
│       │   ├── task.py      # 用户模块定时任务
│       │   └── service.py
│       ├── email/
│       │   ├── __init__.py
│       │   ├── task.py      # 邮件模块定时任务
│       │   └── service.py
│       └── analytics/
│           ├── __init__.py
│           ├── task.py      # 分析模块定时任务
│           └── service.py
```

### 任务定义示例

**app/modules/user/task.py:**

```python
from chronflow import daily, cron

@daily(hour=2, minute=0)
async def cleanup_inactive_users():
    """每天凌晨 2 点清理不活跃用户。"""
    # 业务逻辑
    pass

@cron("0 */15 * * * *")
async def sync_user_profiles():
    """每 15 分钟同步用户资料。"""
    # 业务逻辑
    pass
```

**app/modules/email/task.py:**

```python
from chronflow import interval, every

@interval(60)
async def send_pending_emails():
    """每分钟发送待发邮件。"""
    # 业务逻辑
    pass

@every(hours=1)
async def cleanup_email_queue():
    """每小时清理邮件队列。"""
    # 业务逻辑
    pass
```

### 主程序集成

**app/main.py:**

```python
import asyncio
from chronflow import Scheduler, SchedulerConfig

async def main():
    # 初始化调度器
    config = SchedulerConfig(
        max_workers=10,
        enable_logging=True,
    )
    scheduler = Scheduler(config=config)

    # 自动发现并注册所有模块的任务
    tasks = scheduler.discover_tasks_from_directory(
        "app/modules",
        pattern="task.py",
        recursive=True,
    )

    print(f"已注册 {len(tasks)} 个定时任务")

    # 启动调度器
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 高级用法

### 排除特定文件

```python
# 排除测试文件和备份文件
tasks = scheduler.discover_tasks_from_directory(
    "app",
    pattern="*.py",
    exclude_patterns=[
        "test_*.py",      # 测试文件
        "*_backup.py",    # 备份文件
        "__init__.py",    # 初始化文件
    ]
)
```

### 非递归扫描

```python
# 只扫描当前目录,不扫描子目录
tasks = scheduler.discover_tasks_from_directory(
    "app/tasks",
    recursive=False
)
```

### 使用 TaskDiscovery 类

如果需要更多控制,可以直接使用 `TaskDiscovery` 类:

```python
from chronflow import Scheduler, TaskDiscovery

scheduler = Scheduler()
discovery = TaskDiscovery(scheduler)

# 发现任务但不自动注册
tasks = discovery.discover_from_directory(
    "app/modules",
    auto_register=False
)

# 手动过滤和注册
for task in tasks:
    if task.config.enabled:
        scheduler.register_task(task)

# 获取所有已发现的任务
all_discovered = discovery.get_discovered_tasks()
```

## 文件名模式

支持的通配符:
- `*` - 匹配任意数量的字符
- `?` - 匹配单个字符

示例:
- `task.py` - 精确匹配
- `*_task.py` - 匹配 `user_task.py`, `email_task.py` 等
- `task*.py` - 匹配 `task.py`, `tasks.py`, `task_user.py` 等
- `*.py` - 匹配所有 Python 文件

## 最佳实践

### 1. 约定优于配置

建立统一的文件命名约定:

```python
# 推荐: 使用统一的文件名
# modules/user/task.py
# modules/email/task.py
# modules/report/task.py

scheduler.discover_tasks_from_directory("modules", pattern="task.py")
```

### 2. 模块化组织

按业务模块组织任务:

```
app/
├── modules/
│   ├── user/
│   │   └── task.py      # 用户相关任务
│   ├── email/
│   │   └── task.py      # 邮件相关任务
│   └── report/
│       └── task.py      # 报表相关任务
```

### 3. 使用有意义的任务名

装饰器会使用函数名作为任务名,确保命名清晰:

```python
# ✅ 好的命名
@daily(hour=2)
async def cleanup_inactive_users():
    pass

# ❌ 不好的命名
@daily(hour=2)
async def task1():
    pass
```

### 4. 错误处理

任务发现会自动跳过导入失败的模块,但应该检查日志:

```python
import logging

logging.basicConfig(level=logging.WARNING)

tasks = scheduler.discover_tasks_from_directory("app/modules")

# 检查是否所有预期的任务都被发现
expected_count = 10
if len(tasks) < expected_count:
    logging.warning(f"预期 {expected_count} 个任务,实际发现 {len(tasks)} 个")
```

### 5. 测试环境排除

在测试环境中排除某些任务:

```python
import os

exclude = ["*_prod.py"] if os.getenv("ENV") == "test" else []

tasks = scheduler.discover_tasks_from_directory(
    "app/modules",
    exclude_patterns=exclude
)
```

## 与传统方式对比

### 传统方式

```python
from chronflow import Scheduler
from app.tasks.user_tasks import cleanup_users, sync_users
from app.tasks.email_tasks import send_emails, cleanup_emails
from app.tasks.report_tasks import daily_report, weekly_report

scheduler = Scheduler()
# 需要手动导入和注册每个任务...
```

### 使用自动发现

```python
from chronflow import Scheduler

scheduler = Scheduler()

# 一行代码完成所有任务的发现和注册
scheduler.discover_tasks_from_directory("app/tasks")
```

## 注意事项

1. **导入副作用** - 发现任务时会导入模块,可能触发模块级代码执行
2. **命名冲突** - 确保任务名称唯一,重复的任务名会被跳过
3. **循环导入** - 避免在任务文件中创建循环导入
4. **性能影响** - 大量文件扫描可能影响启动时间,建议在应用启动时执行一次

## 完整示例

查看 `examples/task_discovery_example.py` 和 `examples/project_integration_example.py` 获取完整的可运行示例。

## 相关文档

- [快速开始](../README.md#快速开始)
- [装饰器 API](decorators.md)
- [任务配置](configuration.md)
