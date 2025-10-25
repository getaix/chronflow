# Logging

Symphra Scheduler provides a pluggable logging system that lets you use your preferred logging library.

## Supported Libraries

### Structlog (default)

If structlog is installed, Symphra Scheduler uses it by default:

```python
from symphra_scheduler import Scheduler

# Automatically uses structlog (if installed)
scheduler = Scheduler()
```

Install structlog:

```bash
pip install symphra-scheduler[structlog]
```

### Loguru

Use loguru as the logging library:

```python
from loguru import logger
from symphra_scheduler import Scheduler
from symphra_scheduler.logging import LoguruAdapter

# Configure loguru
logger.add("scheduler.log", rotation="1 day", retention="7 days")

# Use loguru adapter
scheduler = Scheduler(logger=LoguruAdapter(logger))
```

Install loguru:

```bash
pip install symphra-scheduler[loguru]
```

### Python standard library logging

Use Python's built-in logging module:

```python
import logging
from symphra_scheduler import Scheduler
from symphra_scheduler.logging import StdlibAdapter

# Configure stdlib logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("symphra_scheduler")

# Use stdlib adapter
scheduler = Scheduler(logger=StdlibAdapter(logger))
```

### Disable logging

If you don't need any log output:

```python
from symphra_scheduler import Scheduler
from symphra_scheduler.logging import NoOpAdapter

scheduler = Scheduler(logger=NoOpAdapter())
```

## Custom Logger Adapter

You can implement your own adapter:

```python
from symphra_scheduler.logging import LoggerAdapter

class MyCustomLogger(LoggerAdapter):
    """Custom logger adapter."""

    def __init__(self, logger):
        self._logger = logger

    def debug(self, message: str, **kwargs):
        self._logger.debug(f"{message} - {kwargs}")

    def info(self, message: str, **kwargs):
        self._logger.info(f"{message} - {kwargs}")

    def warning(self, message: str, **kwargs):
        self._logger.warning(f"{message} - {kwargs}")

    def error(self, message: str, **kwargs):
        self._logger.error(f"{message} - {kwargs}")

    def critical(self, message: str, **kwargs):
        self._logger.critical(f"{message} - {kwargs}")

# Use the custom adapter
scheduler = Scheduler(logger=MyCustomLogger(my_logger))
```

## Log Level Configuration

Control log levels via config file:

```toml
# config.toml
enable_logging = true
log_level = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

```python
from symphra_scheduler import Scheduler, SchedulerConfig

config = SchedulerConfig.from_file("config.toml")
scheduler = Scheduler(config=config)
```

## Log Output Example

Typical output:

```
2025-10-22 10:30:00 - symphra_scheduler - INFO - Scheduler started
2025-10-22 10:30:05 - symphra_scheduler - INFO - Task 'health_check' scheduled
2025-10-22 10:30:05 - symphra_scheduler - INFO - Task 'health_check' started
2025-10-22 10:30:06 - symphra_scheduler - INFO - Task 'health_check' completed in 1.23s
2025-10-10 - symphra_scheduler - WARNING - Task 'sync_data' failed, retry attempt 1/3
2025-10-12 - symphra_scheduler - INFO - Task 'sync_data' completed after retry
```

## Log Context

Adapters support structured context data:

```python
from loguru import logger
from symphra_scheduler.logging import LoguruAdapter

logger.configure(
    handlers=[
        {
            "sink": "scheduler.log",
            "format": "{time} {level} {message} {extra}",
            "serialize": True  # JSON output
        }
    ]
)

scheduler = Scheduler(logger=LoguruAdapter(logger))
```

Each log will include structured fields such as task name and execution time.
