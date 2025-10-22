"""日志模块测试。"""

import logging
from typing import Any

import pytest

from chronflow.logging import (
    LoggerAdapter,
    NoOpAdapter,
    StdlibAdapter,
    get_default_logger,
)


class TestLoggerAdapter:
    """日志适配器抽象类测试。"""

    def test_abstract_class(self):
        """测试抽象类不能直接实例化。"""
        with pytest.raises(TypeError):
            LoggerAdapter()  # type: ignore


class TestNoOpAdapter:
    """NoOp 适配器测试。"""

    def test_creation(self):
        """测试创建 NoOp 适配器。"""
        logger = NoOpAdapter()
        assert logger is not None

    def test_debug(self):
        """测试 debug 方法不报错。"""
        logger = NoOpAdapter()
        logger.debug("test message", key="value")

    def test_info(self):
        """测试 info 方法不报错。"""
        logger = NoOpAdapter()
        logger.info("test message", key="value")

    def test_warning(self):
        """测试 warning 方法不报错。"""
        logger = NoOpAdapter()
        logger.warning("test message", key="value")

    def test_error(self):
        """测试 error 方法不报错。"""
        logger = NoOpAdapter()
        logger.error("test message", key="value")

    def test_exception(self):
        """测试 exception 方法不报错。"""
        logger = NoOpAdapter()
        logger.exception("test message", key="value")


class TestStdlibAdapter:
    """标准库日志适配器测试。"""

    def test_creation(self):
        """测试创建标准库适配器。"""
        stdlib_logger = logging.getLogger("test")
        adapter = StdlibAdapter(stdlib_logger)
        assert adapter._logger == stdlib_logger

    def test_debug(self, caplog):
        """测试 debug 方法。"""
        stdlib_logger = logging.getLogger("test_debug")
        stdlib_logger.setLevel(logging.DEBUG)
        adapter = StdlibAdapter(stdlib_logger)

        with caplog.at_level(logging.DEBUG, logger="test_debug"):
            adapter.debug("debug message", key="value")

        assert "debug message" in caplog.text

    def test_info(self, caplog):
        """测试 info 方法。"""
        stdlib_logger = logging.getLogger("test_info")
        adapter = StdlibAdapter(stdlib_logger)

        with caplog.at_level(logging.INFO, logger="test_info"):
            adapter.info("info message", key="value")

        assert "info message" in caplog.text

    def test_warning(self, caplog):
        """测试 warning 方法。"""
        stdlib_logger = logging.getLogger("test_warning")
        adapter = StdlibAdapter(stdlib_logger)

        with caplog.at_level(logging.WARNING, logger="test_warning"):
            adapter.warning("warning message", key="value")

        assert "warning message" in caplog.text

    def test_error(self, caplog):
        """测试 error 方法。"""
        stdlib_logger = logging.getLogger("test_error")
        adapter = StdlibAdapter(stdlib_logger)

        with caplog.at_level(logging.ERROR, logger="test_error"):
            adapter.error("error message", key="value")

        assert "error message" in caplog.text

    def test_exception(self, caplog):
        """测试 exception 方法。"""
        stdlib_logger = logging.getLogger("test_exception")
        adapter = StdlibAdapter(stdlib_logger)

        with caplog.at_level(logging.ERROR, logger="test_exception"):
            adapter.exception("exception message", key="value")

        assert "exception message" in caplog.text


class TestStructlogAdapter:
    """Structlog 适配器测试。"""

    def test_creation_with_structlog(self):
        """测试使用 structlog 创建适配器。"""
        try:
            import structlog

            logger = structlog.get_logger()
            from chronflow.logging import StructlogAdapter

            adapter = StructlogAdapter(logger)
            # structlog 的 logger 可能被包装，所以我们只检查类型
            assert adapter is not None
        except ImportError:
            pytest.skip("structlog not installed")

    def test_methods_with_structlog(self):
        """测试所有日志方法。"""
        try:
            import structlog

            logger = structlog.get_logger()
            from chronflow.logging import StructlogAdapter

            adapter = StructlogAdapter(logger)

            # 这些方法应该不报错
            adapter.debug("debug", key="value")
            adapter.info("info", key="value")
            adapter.warning("warning", key="value")
            adapter.error("error", key="value")
            adapter.exception("exception", key="value")

        except ImportError:
            pytest.skip("structlog not installed")


class TestLoguruAdapter:
    """Loguru 适配器测试。"""

    def test_creation_with_loguru(self):
        """测试使用 loguru 创建适配器。"""
        try:
            from loguru import logger

            from chronflow.logging import LoguruAdapter

            adapter = LoguruAdapter(logger)
            assert adapter._logger == logger
        except ImportError:
            pytest.skip("loguru not installed")

    def test_methods_with_loguru(self):
        """测试所有日志方法。"""
        try:
            from loguru import logger

            from chronflow.logging import LoguruAdapter

            adapter = LoguruAdapter(logger)

            # 这些方法应该不报错
            adapter.debug("debug", key="value")
            adapter.info("info", key="value")
            adapter.warning("warning", key="value")
            adapter.error("error", key="value")
            adapter.exception("exception", key="value")

        except ImportError:
            pytest.skip("loguru not installed")


class TestGetDefaultLogger:
    """测试获取默认日志器。"""

    def test_get_default_logger_with_structlog(self):
        """测试当 structlog 可用时获取默认日志器。"""
        try:
            import structlog  # noqa: F401

            logger = get_default_logger()
            from chronflow.logging import StructlogAdapter

            assert isinstance(logger, StructlogAdapter)
        except ImportError:
            pytest.skip("structlog not installed")

    def test_get_default_logger_fallback(self):
        """测试 NoOp 适配器作为 fallback。"""
        # 这个测试验证 get_default_logger 可以正常工作
        logger = get_default_logger()
        assert logger is not None
        # 默认应该返回 StructlogAdapter（如果 structlog 可用）或 StdlibAdapter
        assert isinstance(logger, StdlibAdapter | NoOpAdapter) or hasattr(logger, "_logger")


class TestCustomAdapter:
    """测试自定义适配器。"""

    def test_custom_adapter(self):
        """测试用户可以创建自定义适配器。"""

        class CustomLogger(LoggerAdapter):
            """自定义日志适配器。"""

            def __init__(self):
                self.messages: list[tuple[str, str, dict[str, Any]]] = []

            def debug(self, message: str, **kwargs: Any) -> None:
                self.messages.append(("debug", message, kwargs))

            def info(self, message: str, **kwargs: Any) -> None:
                self.messages.append(("info", message, kwargs))

            def warning(self, message: str, **kwargs: Any) -> None:
                self.messages.append(("warning", message, kwargs))

            def error(self, message: str, **kwargs: Any) -> None:
                self.messages.append(("error", message, kwargs))

            def exception(self, message: str, **kwargs: Any) -> None:
                self.messages.append(("exception", message, kwargs))

        logger = CustomLogger()
        logger.info("test", key="value")

        assert len(logger.messages) == 1
        assert logger.messages[0] == ("info", "test", {"key": "value"})
