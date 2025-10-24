"""可插拔的日志系统,支持多种日志库。"""  # noqa: A005

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoggerAdapter(ABC):
    """日志适配器抽象基类。

    用户可以实现此接口来适配自己喜欢的日志库。
    """

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试信息。"""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """记录一般信息。"""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告信息。"""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """记录错误信息。"""
        pass

    @abstractmethod
    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常信息(包含堆栈)。"""
        pass


class StructlogAdapter(LoggerAdapter):
    """Structlog 日志适配器(默认)。"""

    def __init__(self, logger_name: str = "chronflow") -> None:
        """初始化 structlog 适配器。

        参数:
            logger_name: 日志记录器名称
        """
        try:
            import structlog

            self._logger = structlog.get_logger(logger_name)
        except ImportError:
            # 如果没有 structlog,回退到标准库
            import logging

            self._logger = logging.getLogger(logger_name)
            self._is_stdlib = True
        else:
            self._is_stdlib = False

    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试信息。"""
        if self._is_stdlib:
            self._logger.debug(message, extra=kwargs)
        else:
            self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """记录一般信息。"""
        if self._is_stdlib:
            self._logger.info(message, extra=kwargs)
        else:
            self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告信息。"""
        if self._is_stdlib:
            self._logger.warning(message, extra=kwargs)
        else:
            self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """记录错误信息。"""
        # 避免 exc_info 字段冲突
        exc_info = kwargs.pop("exc_info", None)
        if self._is_stdlib:
            self._logger.error(message, extra=kwargs, exc_info=exc_info)
        else:
            if exc_info:
                kwargs["exc_info"] = exc_info
            self._logger.error(message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常信息。"""
        if self._is_stdlib:
            self._logger.exception(message, extra=kwargs)
        else:
            # structlog 使用 exc_info=True
            kwargs["exc_info"] = True
            self._logger.error(message, **kwargs)


class LoguruAdapter(LoggerAdapter):
    """Loguru 日志适配器。

    示例:
        from loguru import logger
        from chronflow.logging import LoguruAdapter

        scheduler = Scheduler()
        scheduler.set_logger(LoguruAdapter(logger))
    """

    def __init__(self, logger: Any) -> None:
        """初始化 loguru 适配器。

        参数:
            logger: loguru.logger 实例
        """
        self._logger = logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试信息。"""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """记录一般信息。"""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告信息。"""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """记录错误信息。"""
        # exc_info 不需要传递,loguru 会自动处理
        kwargs.pop("exc_info", None)
        self._logger.error(message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常信息。"""
        self._logger.exception(message, **kwargs)


class StdlibAdapter(LoggerAdapter):
    """Python 标准库 logging 适配器。

    示例:
        import logging
        from chronflow.logging import StdlibAdapter

        logger = logging.getLogger("myapp")
        scheduler = Scheduler()
        scheduler.set_logger(StdlibAdapter(logger))
    """

    def __init__(self, logger: Any) -> None:
        """初始化标准库适配器。

        参数:
            logger: logging.Logger 实例
        """
        self._logger = logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试信息。"""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """记录一般信息。"""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告信息。"""
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """记录错误信息。"""
        # 避免 exc_info 字段冲突
        exc_info = kwargs.pop("exc_info", None)
        self._logger.error(message, extra=kwargs, exc_info=exc_info)

    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常信息。"""
        self._logger.exception(message, extra=kwargs)


class NoOpAdapter(LoggerAdapter):
    """空操作日志适配器,不输出任何日志。

    用于完全禁用日志输出。
    """

    def debug(self, message: str, **kwargs: Any) -> None:
        """不记录。"""
        pass

    def info(self, message: str, **kwargs: Any) -> None:
        """不记录。"""
        pass

    def warning(self, message: str, **kwargs: Any) -> None:
        """不记录。"""
        pass

    def error(self, message: str, **kwargs: Any) -> None:
        """不记录。"""
        pass

    def exception(self, message: str, **kwargs: Any) -> None:
        """不记录。"""
        pass


def get_default_logger() -> LoggerAdapter:
    """获取默认日志适配器。

    按优先级尝试:
    1. structlog (如果已安装)
    2. Python 标准库 logging

    返回值:
        日志适配器实例
    """
    try:
        return StructlogAdapter()
    except Exception:
        import logging

        return StdlibAdapter(logging.getLogger("chronflow"))
