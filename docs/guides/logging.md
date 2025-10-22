# 日志系统

chronflow 提供了可插拔的日志系统，允许你使用自己喜欢的日志库。

## 支持的日志库

### Structlog (默认)

如果安装了 structlog，chronflow 会默认使用它：

```python
from chronflow import Scheduler

# 自动使用 structlog（如果已安装）
scheduler = Scheduler()
```

安装 structlog：

```bash
pip install chronflow[structlog]
```

### Loguru

使用 loguru 作为日志库：

```python
from loguru import logger
from chronflow import Scheduler
from chronflow.logging import LoguruAdapter

# 配置 loguru
logger.add("scheduler.log", rotation="1 day", retention="7 days")

# 使用 loguru 适配器
scheduler = Scheduler(logger=LoguruAdapter(logger))
```

安装 loguru：

```bash
pip install chronflow[loguru]
```

### Python 标准库 logging

使用 Python 内置的 logging 模块：

```python
import logging
from chronflow import Scheduler
from chronflow.logging import StdlibAdapter

# 配置标准库日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("chronflow")

# 使用标准库适配器
scheduler = Scheduler(logger=StdlibAdapter(logger))
```

### 禁用日志

如果不需要日志输出：

```python
from chronflow import Scheduler
from chronflow.logging import NoOpAdapter

scheduler = Scheduler(logger=NoOpAdapter())
```

## 自定义日志适配器

你可以实现自己的日志适配器：

```python
from chronflow.logging import LoggerAdapter

class MyCustomLogger(LoggerAdapter):
    """自定义日志适配器。"""

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

# 使用自定义适配器
scheduler = Scheduler(logger=MyCustomLogger(my_logger))
```

## 日志级别配置

通过配置文件控制日志级别：

```toml
# config.toml
enable_logging = true
log_level = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

```python
from chronflow import Scheduler, SchedulerConfig

config = SchedulerConfig.from_file("config.toml")
scheduler = Scheduler(config=config)
```

## 日志输出示例

典型的日志输出：

```
2025-10-22 10:30:00 - chronflow - INFO - Scheduler started
2025-10-22 10:30:05 - chronflow - INFO - Task 'health_check' scheduled
2025-10-22 10:30:05 - chronflow - INFO - Task 'health_check' started
2025-10-22 10:30:06 - chronflow - INFO - Task 'health_check' completed in 1.23s
2025-10-22 10:30:10 - chronflow - WARNING - Task 'sync_data' failed, retry attempt 1/3
2025-10-22 10:30:12 - chronflow - INFO - Task 'sync_data' completed after retry
```

## 日志上下文

日志适配器支持结构化上下文数据：

```python
from loguru import logger
from chronflow.logging import LoguruAdapter

logger.configure(
    handlers=[
        {
            "sink": "scheduler.log",
            "format": "{time} {level} {message} {extra}",
            "serialize": True  # JSON 格式
        }
    ]
)

scheduler = Scheduler(logger=LoguruAdapter(logger))
```

这样每条日志都会包含任务名称、执行时间等结构化信息。
