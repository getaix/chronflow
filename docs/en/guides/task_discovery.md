# Automatic Task Discovery

Symphra Scheduler provides a powerful automatic task discovery mechanism that can scan project directories or packages to find and register scheduled tasks defined with decorators. This greatly simplifies integration.

## Features

- Directory scan — automatically scan Python files under a directory
- Package import — discover tasks from installed Python packages
- Custom patterns — glob-style filename matching (`task.py`, `*_tasks.py`, etc.)
- Recursive scanning — search subdirectories recursively
- Flexible filters — exclude specific files or patterns
- Auto registration — discovered tasks are registered to the scheduler
- Error tolerance — modules that fail to import are skipped without affecting others

## Basic Usage

### Discover from a directory

Fits module-oriented project structures:

```python
from symphra_scheduler import Scheduler

scheduler = Scheduler()

# Scan all task.py files under the directory
tasks = scheduler.discover_tasks_from_directory("app/modules")

# Discovered tasks are automatically registered to the scheduler
print(f"Discovered {len(tasks)} tasks")
```

### Use custom filename patterns

```python
# Scan all *_tasks.py files
tasks = scheduler.discover_tasks_from_directory(
    "app",
    pattern="*_tasks.py",
    exclude_patterns=["test_*.py", "*_backup.py"]
)
```

### Discover from a package

Useful when tasks live in installed Python packages:

```python
# Discover tasks from a package and its subpackages
tasks = scheduler.discover_tasks_from_package("my_app.tasks")
```

### Import from explicit module list

Useful when you want precise control over modules to load:

```python
tasks = scheduler.discover_tasks_from_modules([
    "my_app.tasks.user_tasks",
    "my_app.tasks.email_tasks",
    "my_app.tasks.report_tasks",
])
```

## Real-world Project Example

### Project structure

```
my_project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── modules/
│       ├── __init__.py
│       ├── user/
│       │   ├── __init__.py
│       │   ├── task.py      # User module scheduled tasks
│       │   └── service.py
│       ├── email/
│       │   ├── __init__.py
│       │   ├── task.py      # Email module scheduled tasks
│       │   └── service.py
│       └── analytics/
│           ├── __init__.py
│           ├── task.py      # Analytics module scheduled tasks
│           └── service.py
```

### Task definition examples

**app/modules/user/task.py:**

```python
from symphra_scheduler import daily, cron

@daily(hour=2, minute=0)
async def cleanup_inactive_users():
    """Clean up inactive users at 2:00 AM daily."""
    # business logic
    pass

@cron("0 */15 * * * *")
async def sync_user_profiles():
    """Synchronize user profiles every 15 minutes."""
    # business logic
    pass
```

**app/modules/email/task.py:**

```python
from symphra_scheduler import interval, every

@interval(60)
async def send_pending_emails():
    """Send pending emails every minute."""
    # business logic
    pass

@every(hours=1)
async def cleanup_email_queue():
    """Clean up email queue hourly."""
    # business logic
    pass
```

### Main integration

**app/main.py:**

```python
import asyncio
from symphra_scheduler import Scheduler, SchedulerConfig

async def main():
    # Initialize scheduler
    config = SchedulerConfig(
        max_workers=10,
        enable_logging=True,
    )
    scheduler = Scheduler(config=config)

    # Auto-discover and register all module tasks
    tasks = scheduler.discover_tasks_from_directory(
        "app/modules",
        pattern="task.py",
        recursive=True,
    )

    print(f"Registered {len(tasks)} scheduled tasks")

    # Start scheduler
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Exclude specific files

```python
# Exclude test files and backups
tasks = scheduler.discover_tasks_from_directory(
    "app",
    pattern="*.py",
    exclude_patterns=[
        "test_*.py",      # test files
        "*_backup.py",    # backup files
        "__init__.py",    # package init files
    ]
)
```

### Non-recursive scan

```python
# Scan only the current directory, not subdirectories
tasks = scheduler.discover_tasks_from_directory(
    "app/tasks",
    recursive=False
)
```

### Using TaskDiscovery class

If you need more control, use the `TaskDiscovery` class directly:

```python
from symphra_scheduler import Scheduler, TaskDiscovery

scheduler = Scheduler()
discovery = TaskDiscovery(scheduler)

# Discover tasks without auto-registration
tasks = discovery.discover_from_directory(
    "app/modules",
    auto_register=False
)

# Manual filter and register
for task in tasks:
    if task.config.enabled:
        scheduler.register_task(task)

# Get all discovered tasks
all_discovered = discovery.get_discovered_tasks()
```

## Filename Patterns

Supported wildcards:
- `*` — matches any number of characters
- `?` — matches a single character

Examples:
- `task.py` — exact match
- `*_task.py` — matches `user_task.py`, `email_task.py`, etc.
- `task*.py` — matches `task.py`, `tasks.py`, `task_user.py`, etc.
- `*.py` — matches all Python files

## Best Practices

### 1. Convention over configuration

Establish a unified file naming convention:

```python
# Recommended: use a single filename convention
# modules/user/task.py
# modules/email/task.py
# modules/report/task.py

scheduler.discover_tasks_from_directory("modules", pattern="task.py")
```

### 2. Modular organization

Organize tasks by business modules:

```
app/
├── modules/
│   ├── user/
│   │   └── task.py      # User-related tasks
│   ├── email/
│   │   └── task.py      # Email-related tasks
│   └── report/
│       └── task.py      # Report-related tasks
```

### 3. Use meaningful task names

Decorators use function names as task names. Keep names clear:

```python
# ✅ Good naming
@daily(hour=2)
async def cleanup_inactive_users():
    pass

# ❌ Poor naming
@daily(hour=2)
async def task1():
    pass
```

### 4. Error handling

Task discovery skips modules that fail to import, but you should check logs:

```python
import logging

logging.basicConfig(level=logging.WARNING)

tasks = scheduler.discover_tasks_from_directory("app/modules")

# Check whether all expected tasks are discovered
expected_count = 10
if len(tasks) < expected_count:
    logging.warning(f"Expected {expected_count} tasks, actually discovered {len(tasks)}")
```

### 5. Exclude in test environments

Exclude certain tasks in test environments:

```python
import os

exclude = ["*_prod.py"] if os.getenv("ENV") == "test" else []

tasks = scheduler.discover_tasks_from_directory(
    "app/modules",
    exclude_patterns=exclude
)
```

## Comparison with the traditional way

### Traditional approach

```python
from symphra_scheduler import Scheduler
from app.tasks.user_tasks import cleanup_users, sync_users
from app.tasks.email_tasks import send_emails, cleanup_emails
from app.tasks.report_tasks import daily_report, weekly_report

scheduler = Scheduler()
# You must manually import and register each task...
```

### Using auto-discovery

```python
from symphra_scheduler import Scheduler

scheduler = Scheduler()

# One line to discover and register all tasks
scheduler.discover_tasks_from_directory("app/tasks")
```

## Notes

1. Import side effects — task discovery imports modules and may trigger module-level code
2. Name conflicts — ensure task names are unique; duplicates are skipped
3. Circular imports — avoid circular dependencies in task modules
4. Performance impact — scanning many files can affect startup time; run once at app start

## Complete Examples

See `examples/task_discovery_example.py` and `examples/project_integration_example.py` for complete runnable examples.

## Related Docs

- [Quickstart](../quickstart.md)
- [Decorator API](../api/decorators.md)
- [Task Config](../api/config.md)
