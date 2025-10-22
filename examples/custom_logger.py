"""自定义日志示例 - 展示如何使用不同的日志库。"""

import asyncio
from datetime import datetime

from chronflow import Scheduler, interval


def example_stdlib_logging():
    """示例 1: 使用 Python 标准库 logging。"""
    import logging

    from chronflow.logging import StdlibAdapter

    # 配置标准库 logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("myapp")

    # 创建调度器并设置日志
    scheduler = Scheduler(logger=StdlibAdapter(logger))

    @interval(5)
    async def task_with_stdlib():
        pass

    return scheduler


def example_loguru():
    """示例 2: 使用 Loguru (需要安装: pip install loguru)。"""
    try:
        from loguru import logger

        from chronflow.logging import LoguruAdapter

        # 配置 loguru
        logger.remove()  # 移除默认处理器
        logger.add(
            lambda msg: print(msg, end=""),  # noqa: T201
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>",
        )

        # 创建调度器并设置 loguru
        scheduler = Scheduler(logger=LoguruAdapter(logger))

        @interval(5)
        async def task_with_loguru():
            pass

        return scheduler

    except ImportError:
        return None


def example_no_logging():
    """示例 3: 完全禁用日志输出。"""
    from chronflow.logging import NoOpAdapter

    # 方法 1: 使用 NoOpAdapter
    scheduler = Scheduler(logger=NoOpAdapter())

    # 方法 2: 通过配置禁用
    # config = SchedulerConfig(enable_logging=False)
    # scheduler = Scheduler(config=config)

    @interval(5)
    async def silent_task():
        pass

    return scheduler


def example_custom_logger():
    """示例 4: 自定义日志适配器。"""
    from typing import Any

    from chronflow.logging import LoggerAdapter

    class ColoredConsoleAdapter(LoggerAdapter):
        """彩色控制台日志适配器。"""

        COLORS = {
            "DEBUG": "\033[36m",  # 青色
            "INFO": "\033[32m",  # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",  # 红色
            "RESET": "\033[0m",  # 重置
        }

        def _log(self, level: str, message: str, **kwargs: Any) -> None:
            """彩色日志输出。"""
            self.COLORS.get(level, "")
            self.COLORS["RESET"]
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 格式化额外参数
            " ".join(f"{k}={v}" for k, v in kwargs.items())


        def debug(self, message: str, **kwargs: Any) -> None:
            self._log("DEBUG", message, **kwargs)

        def info(self, message: str, **kwargs: Any) -> None:
            self._log("INFO", message, **kwargs)

        def warning(self, message: str, **kwargs: Any) -> None:
            self._log("WARNING", message, **kwargs)

        def error(self, message: str, **kwargs: Any) -> None:
            self._log("ERROR", message, **kwargs)

        def exception(self, message: str, **kwargs: Any) -> None:
            self._log("ERROR", message, **kwargs)

    # 使用自定义日志
    scheduler = Scheduler(logger=ColoredConsoleAdapter())

    @interval(5)
    async def custom_logger_task():
        pass

    return scheduler


async def main():
    """主函数。"""

    choice = input("请选择 (1-4): ").strip()

    if choice == "1":
        scheduler = example_stdlib_logging()
    elif choice == "2":
        scheduler = example_loguru()
        if not scheduler:
            return
    elif choice == "3":
        scheduler = example_no_logging()
    elif choice == "4":
        scheduler = example_custom_logger()
    else:
        return


    try:
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
