"""后端注册系统测试。"""

import pytest

from chronflow.backends import (
    create_backend,
    get_registered_backends,
    register_backend,
)
from chronflow.backends.base import QueueBackend
from chronflow.backends.memory import MemoryBackend


class DummyBackend(QueueBackend):
    """测试用虚拟后端。"""

    def __init__(self, test_param: str = "default") -> None:
        self.test_param = test_param

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def enqueue(self, task_id, task_name, scheduled_time, payload, priority=0) -> None:
        pass

    async def dequeue(self, limit=1) -> list[dict]:
        return []

    async def acknowledge(self, task_id) -> None:
        pass

    async def reject(self, task_id, requeue=False) -> None:
        pass

    async def get_queue_size(self) -> int:
        return 0

    async def clear(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True


class TestBackendRegistry:
    """后端注册系统测试类。"""

    def test_register_simple_backend(self):
        """测试注册简单后端。"""
        register_backend("test_simple", lambda **opts: DummyBackend(**opts), override=True)

        assert "test_simple" in get_registered_backends()

        backend = create_backend("test_simple")
        assert isinstance(backend, DummyBackend)
        assert backend.test_param == "default"

    def test_register_backend_with_options(self):
        """测试注册带参数的后端。"""
        register_backend("test_with_opts", lambda **opts: DummyBackend(**opts), override=True)

        backend = create_backend("test_with_opts", test_param="custom_value")
        assert isinstance(backend, DummyBackend)
        assert backend.test_param == "custom_value"

    def test_register_backend_case_insensitive(self):
        """测试后端名称不区分大小写。"""
        register_backend("TEST_CASE", lambda **opts: DummyBackend(**opts), override=True)

        # 使用不同大小写创建
        backend1 = create_backend("test_case")
        backend2 = create_backend("TEST_CASE")
        backend3 = create_backend("Test_Case")

        assert isinstance(backend1, DummyBackend)
        assert isinstance(backend2, DummyBackend)
        assert isinstance(backend3, DummyBackend)

    def test_register_backend_empty_name_raises_error(self):
        """测试空后端名称抛出错误。"""
        with pytest.raises(ValueError, match="后端名称不能为空"):
            register_backend("", lambda **opts: DummyBackend(**opts))

        with pytest.raises(ValueError, match="后端名称不能为空"):
            register_backend("   ", lambda **opts: DummyBackend(**opts))

    def test_register_duplicate_backend_raises_error(self):
        """测试重复注册后端抛出错误。"""
        register_backend("test_dup", lambda **opts: DummyBackend(**opts), override=True)

        with pytest.raises(ValueError, match="已注册"):
            register_backend("test_dup", lambda **opts: DummyBackend(**opts))

    def test_register_duplicate_backend_with_override(self):
        """测试使用 override 参数覆盖后端。"""
        # 第一次注册
        register_backend(
            "test_override",
            lambda **opts: DummyBackend(test_param="original"),
            override=True,
        )

        backend1 = create_backend("test_override")
        assert backend1.test_param == "original"

        # 覆盖注册
        register_backend(
            "test_override",
            lambda **opts: DummyBackend(test_param="overridden"),
            override=True,
        )

        backend2 = create_backend("test_override")
        assert backend2.test_param == "overridden"

    def test_create_backend_unregistered_raises_error(self):
        """测试创建未注册的后端抛出错误。"""
        with pytest.raises(ValueError, match="未注册的队列后端"):
            create_backend("nonexistent_backend")

    def test_get_registered_backends_sorted(self):
        """测试获取已注册后端列表按字母排序。"""
        # 注册多个后端(确保覆盖以避免冲突)
        register_backend("zebra", lambda **opts: DummyBackend(**opts), override=True)
        register_backend("apple", lambda **opts: DummyBackend(**opts), override=True)
        register_backend("mango", lambda **opts: DummyBackend(**opts), override=True)

        backends = get_registered_backends()

        # 检查是否包含测试后端
        assert "zebra" in backends
        assert "apple" in backends
        assert "mango" in backends

        # 检查顺序(提取测试后端)
        test_backends = [b for b in backends if b in ["zebra", "apple", "mango"]]
        assert test_backends == ["apple", "mango", "zebra"]

    def test_builtin_backends_registered(self):
        """测试内置后端已注册。"""
        backends = get_registered_backends()

        assert "memory" in backends
        assert "sqlite" in backends
        assert "redis" in backends  # 延迟加载
        assert "rabbitmq" in backends  # 延迟加载

    def test_create_memory_backend(self):
        """测试创建内存后端。"""
        backend = create_backend("memory", max_size=1000)

        assert isinstance(backend, MemoryBackend)
        assert backend.max_size == 1000

    def test_create_sqlite_backend(self):
        """测试创建 SQLite 后端。"""
        backend = create_backend("sqlite", db_path=":memory:")

        from chronflow.backends.sqlite_backend import SQLiteBackend

        assert isinstance(backend, SQLiteBackend)

    def test_lazy_backend_import_error(self):
        """测试延迟加载后端依赖缺失时的错误处理。"""
        # 注册一个引用不存在模块的延迟后端
        from chronflow.backends import _lazy_backend

        register_backend(
            "test_missing_dep",
            _lazy_backend("nonexistent.module", "NonexistentBackend"),
            override=True,
        )

        # 创建时应抛出 ModuleNotFoundError
        with pytest.raises(ModuleNotFoundError):
            create_backend("test_missing_dep")

    def test_backend_factory_with_default_params(self):
        """测试后端工厂函数可以设置默认参数。"""

        def redis_like_factory(**options):
            options.setdefault("host", "localhost")
            options.setdefault("port", 6379)
            return DummyBackend(test_param=f"{options['host']}:{options['port']}")

        register_backend("test_redis_like", redis_like_factory, override=True)

        # 使用默认参数
        backend1 = create_backend("test_redis_like")
        assert backend1.test_param == "localhost:6379"

        # 覆盖默认参数
        backend2 = create_backend("test_redis_like", host="redis.example.com", port=6380)
        assert backend2.test_param == "redis.example.com:6380"

    def test_backend_factory_error_propagation(self):
        """测试后端工厂函数中的错误会正确传播。"""

        def failing_factory(**options):
            raise RuntimeError("Factory initialization failed")

        register_backend("test_failing", failing_factory, override=True)

        with pytest.raises(RuntimeError, match="Factory initialization failed"):
            create_backend("test_failing")

    def test_backend_registry_isolation(self):
        """测试后端注册表不会意外污染全局状态。"""
        # 获取初始后端数量
        initial_backends = set(get_registered_backends())

        # 注册测试后端
        register_backend("test_isolation", lambda **opts: DummyBackend(**opts), override=True)

        # 验证注册成功
        assert "test_isolation" in get_registered_backends()

        # 验证其他后端未受影响
        current_backends = set(get_registered_backends())
        assert initial_backends.issubset(current_backends)
        assert current_backends - initial_backends == {"test_isolation"}
