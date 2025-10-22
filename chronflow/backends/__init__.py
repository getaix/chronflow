"""适用于不同存储系统的队列后端实现。"""

from chronflow.backends.base import QueueBackend
from chronflow.backends.memory import MemoryBackend
from chronflow.backends.sqlite_backend import SQLiteBackend

__all__ = ["QueueBackend", "MemoryBackend", "SQLiteBackend"]

# 可选后端动态加载
try:
    from chronflow.backends.redis_backend import RedisBackend  # noqa: F401

    __all__.append("RedisBackend")
except ImportError:
    pass

try:
    from chronflow.backends.rabbitmq_backend import RabbitMQBackend  # noqa: F401

    __all__.append("RabbitMQBackend")
except ImportError:
    pass
