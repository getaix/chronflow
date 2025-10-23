"""队列后端模块 - 支持多种存储系统的任务队列实现。

本模块提供了可插拔的后端注册系统,允许调度器使用不同的存储后端(内存、SQLite、Redis、RabbitMQ 等)
来持久化和管理任务队列。

核心功能:
- 后端工厂注册机制: 通过 `register_backend` 注册自定义后端
- 后端实例化: 通过 `create_backend` 根据名称创建后端实例
- 延迟加载可选依赖: Redis 和 RabbitMQ 后端仅在实际使用时才导入

内置后端:
- memory: 内存队列(默认),适用于开发和测试
- sqlite: SQLite 持久化队列,适用于单机部署
- redis: Redis 队列(需安装 redis 依赖),适用于分布式部署
- rabbitmq: RabbitMQ 队列(需安装 aio_pika 依赖),适用于企业级消息队列

使用示例:
    ```python
    from chronflow.backends import register_backend, create_backend

    # 使用内置后端
    backend = create_backend("memory", max_size=1000)

    # 注册自定义后端
    register_backend("my_backend", lambda **opts: MyBackend(**opts))
    backend = create_backend("my_backend", custom_option="value")
    ```
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Dict, List

from chronflow.backends.base import QueueBackend
from chronflow.backends.memory import MemoryBackend
from chronflow.backends.sqlite_backend import SQLiteBackend


BackendFactory = Callable[..., QueueBackend]
"""后端工厂类型,接收关键字参数并返回 QueueBackend 实例的可调用对象。"""

_BACKEND_REGISTRY: Dict[str, BackendFactory] = {}
"""全局后端注册表,存储后端名称到工厂函数的映射。"""


def register_backend(name: str, factory: BackendFactory, *, override: bool = False) -> None:
    """注册新的队列后端工厂到全局注册表。

    后端工厂是一个可调用对象,接收关键字参数并返回 ``QueueBackend`` 实例。
    注册后可通过 ``create_backend(name, **options)`` 创建后端实例。

    参数:
        name: 后端唯一标识符,会被转换为小写(推荐使用简短的英文名)
        factory: 后端工厂函数,签名为 ``(**kwargs) -> QueueBackend``
        override: 是否允许覆盖已存在的后端名称(默认 False)

    异常:
        ValueError: 后端名称为空,或名称已存在且 override=False

    示例:
        ```python
        # 注册简单后端
        register_backend("memory", lambda **opts: MemoryBackend(**opts))

        # 注册带默认参数的后端
        def redis_factory(**options):
            options.setdefault("host", "localhost")
            options.setdefault("port", 6379)
            return RedisBackend(**options)

        register_backend("redis", redis_factory)

        # 覆盖已有后端
        register_backend("memory", my_custom_memory_backend, override=True)
        ```

    注意:
        - 后端名称不区分大小写(内部统一转为小写)
        - 工厂函数应处理所有必需的初始化逻辑
        - 建议使用 lambda 或函数包装器实现工厂
    """
    key = name.strip().lower()
    if not key:
        raise ValueError("后端名称不能为空")

    if key in _BACKEND_REGISTRY and not override:
        raise ValueError(f"后端 '{name}' 已注册,如需覆盖请显式传入 override=True")

    _BACKEND_REGISTRY[key] = factory


def create_backend(name: str, **options: Any) -> QueueBackend:
    """根据注册的后端名称创建队列后端实例。

    从全局注册表中查找后端工厂,并使用提供的选项实例化后端。

    参数:
        name: 已注册的后端名称(不区分大小写)
        **options: 传递给后端构造函数的关键字参数

    返回值:
        实例化的 QueueBackend 对象

    异常:
        ValueError: 后端名称未注册

    示例:
        ```python
        # 创建内存后端
        backend = create_backend("memory", max_size=500)

        # 创建 SQLite 后端
        backend = create_backend("sqlite", db_path="tasks.db")

        # 创建 Redis 后端(延迟加载)
        backend = create_backend("redis", host="localhost", port=6379)
        ```

    注意:
        - 后端名称会被转换为小写后查找
        - 如果后端工厂使用延迟导入,实际依赖会在此时加载
        - 可选依赖缺失会在工厂调用时抛出 ImportError
    """
    key = name.strip().lower()
    try:
        factory = _BACKEND_REGISTRY[key]
    except KeyError as exc:
        raise ValueError(f"未注册的队列后端 '{name}'") from exc
    return factory(**options)


def get_registered_backends() -> List[str]:
    """返回所有已注册的后端名称列表。

    返回值:
        已注册的后端名称列表,按字母顺序排序

    示例:
        ```python
        backends = get_registered_backends()
        print(f"可用后端: {', '.join(backends)}")
        # 输出: 可用后端: memory, rabbitmq, redis, sqlite
        ```

    注意:
        - 返回的名称均为小写
        - 包含内置后端和通过 ``register_backend`` 注册的自定义后端
        - 列表是实时生成的,反映当前注册状态
    """
    return sorted(_BACKEND_REGISTRY.keys())


def _lazy_backend(module_path: str, attr: str) -> BackendFactory:
    """创建延迟导入的后端工厂,用于处理可选依赖。

    返回一个工厂函数,该函数在首次调用时才导入目标模块和后端类,
    从而避免在导入本模块时就要求所有可选依赖都已安装。

    参数:
        module_path: 后端模块的完整路径(如 "chronflow.backends.redis_backend")
        attr: 后端类名(如 "RedisBackend")

    返回值:
        后端工厂函数,调用时才进行实际导入

    设计说明:
        - 延迟导入允许用户仅安装实际使用的后端依赖
        - 如果依赖缺失,错误会在创建后端实例时抛出,而非导入时
        - 这符合"按需加载"的设计原则

    示例:
        ```python
        # 注册延迟加载的 Redis 后端
        register_backend(
            "redis",
            _lazy_backend("chronflow.backends.redis_backend", "RedisBackend")
        )

        # 首次调用时才导入 redis 相关模块
        backend = create_backend("redis", host="localhost")
        ```
    """

    def _factory(**options: Any) -> QueueBackend:
        module = import_module(module_path)
        backend_cls = getattr(module, attr)
        return backend_cls(**options)

    return _factory


# 注册内置后端
register_backend("memory", lambda **opts: MemoryBackend(**opts))
register_backend("sqlite", lambda **opts: SQLiteBackend(**opts))

# 注册可选后端,仅在创建实例时才尝试导入依赖
register_backend("redis", _lazy_backend("chronflow.backends.redis_backend", "RedisBackend"))
register_backend(
    "rabbitmq", _lazy_backend("chronflow.backends.rabbitmq_backend", "RabbitMQBackend")
)

__all__ = [
    "QueueBackend",
    "MemoryBackend",
    "SQLiteBackend",
    "BackendFactory",
    "register_backend",
    "create_backend",
    "get_registered_backends",
]

# 可选导出具体实现(若依赖可用)
try:  # pragma: no cover - 仅在依赖满足时导出
    from chronflow.backends.redis_backend import RedisBackend  # type: ignore

    __all__.append("RedisBackend")
except ImportError:  # pragma: no cover
    pass

try:  # pragma: no cover
    from chronflow.backends.rabbitmq_backend import RabbitMQBackend  # type: ignore

    __all__.append("RabbitMQBackend")
except ImportError:  # pragma: no cover
    pass
