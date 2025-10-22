"""
配置模型和解析模块。

本模块提供:
- SchedulerConfig: 调度器配置类,支持环境变量和文件配置
- TaskMetrics: 任务执行指标类,用于统计任务运行情况
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerConfig(BaseSettings):
    """
    调度器主配置类。

    支持从以下来源加载配置(优先级从高到低):
    1. 直接传入的参数
    2. 环境变量(前缀 FSCHEDULER_)
    3. .env 文件
    4. 默认值

    示例:
        # 使用默认配置
        config = SchedulerConfig()

        # 自定义配置
        config = SchedulerConfig(max_workers=20, log_level="DEBUG")

        # 从环境变量(FSCHEDULER_MAX_WORKERS=20)
        config = SchedulerConfig()
    """

    model_config = SettingsConfigDict(
        env_prefix="FSCHEDULER_",  # 环境变量前缀
        env_file=".env",  # 环境变量文件
        env_file_encoding="utf-8",  # 文件编码
        case_sensitive=False,  # 不区分大小写
    )

    max_workers: int = Field(
        default=10,
        gt=0,
        le=1000,
        description="最大并发工作协程数,控制同时执行的任务数量",
    )

    queue_size: int = Field(
        default=1000,
        gt=0,
        description="待处理任务队列的最大大小,超过此值将拒绝新任务",
    )

    shutdown_timeout: float = Field(
        default=30.0,
        gt=0,
        description="优雅关闭的超时时间(秒),等待运行中任务完成的最长时间",
    )

    enable_logging: bool = Field(
        default=True,
        description="是否启用日志记录,设为 False 可完全禁用日志输出",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别,控制输出的日志详细程度",
    )

    timezone: str = Field(
        default="UTC",
        description="调度时区,用于计算任务执行时间(如 'UTC', 'Asia/Shanghai')",
    )

    persistence_enabled: bool = Field(
        default=False,
        description="是否启用任务持久化,重启后可恢复未完成的任务",
    )

    persistence_path: Path = Field(
        default=Path(".fscheduler_state.json"),
        description="持久化文件路径,用于保存调度器状态",
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """
        验证时区字符串是否有效。

        参数:
            v: 时区字符串,如 'UTC', 'Asia/Shanghai'

        返回值:
            验证通过的时区字符串

        抛出:
            ValueError: 时区字符串无效
        """
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            # 尝试使用该时区创建时间对象,验证是否有效
            datetime.now(ZoneInfo(v))
            return v
        except Exception as e:
            raise ValueError(f"无效的时区 '{v}': {e}") from e

    @classmethod
    def from_file(cls, path: str | Path) -> SchedulerConfig:
        """
        从配置文件加载配置。

        支持的文件格式:
        - JSON (.json)
        - TOML (.toml)
        - YAML (.yaml, .yml)

        参数:
            path: 配置文件路径

        返回值:
            SchedulerConfig 实例

        抛出:
            FileNotFoundError: 配置文件不存在
            ValueError: 不支持的文件格式
            ImportError: 缺少必要的解析库(如 PyYAML)

        示例:
            config = SchedulerConfig.from_file("config.toml")
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        # 读取文件内容
        content = path.read_text(encoding="utf-8")

        # 根据文件扩展名解析
        if path.suffix in [".json"]:
            # JSON 格式
            data = json.loads(content)
        elif path.suffix in [".toml"]:
            # TOML 格式(Python 3.11+ 内置 tomllib)
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore
            data = tomllib.loads(content)
        elif path.suffix in [".yaml", ".yml"]:
            # YAML 格式(需要安装 PyYAML)
            try:
                import yaml

                data = yaml.safe_load(content)
            except ImportError as err:
                raise ImportError(
                    "YAML 配置文件需要 PyYAML 库。安装方式: pip install pyyaml"
                ) from err
        else:
            raise ValueError(
                f"不支持的配置文件格式: {path.suffix}. 支持的格式: .json, .toml, .yaml, .yml"
            )

        return cls(**data)


class TaskMetrics(BaseModel):
    """
    任务执行指标类。

    用于统计和记录任务的执行情况,包括成功率、执行时间等关键指标。

    属性:
        total_runs: 总运行次数
        successful_runs: 成功运行次数
        failed_runs: 失败运行次数
        total_execution_time: 总执行时间(秒)
        average_execution_time: 平均执行时间(秒)
        last_run_time: 最后一次运行时间(秒)
        last_success_time: 最后一次成功时间(秒)
        last_failure_time: 最后一次失败时间(秒)
        consecutive_failures: 连续失败次数
    """

    total_runs: int = 0  # 总运行次数
    successful_runs: int = 0  # 成功次数
    failed_runs: int = 0  # 失败次数
    total_execution_time: float = 0.0  # 总耗时(秒)
    average_execution_time: float = 0.0  # 平均耗时(秒)
    last_run_time: float | None = None  # 最后执行耗时
    last_success_time: float | None = None  # 最后成功耗时
    last_failure_time: float | None = None  # 最后失败耗时
    consecutive_failures: int = 0  # 连续失败计数

    def update_success(self, execution_time: float) -> None:
        """
        更新成功执行的指标。

        在任务成功执行后调用,更新相关统计数据。

        参数:
            execution_time: 本次执行耗时(秒)
        """
        self.total_runs += 1  # 总次数加1
        self.successful_runs += 1  # 成功次数加1
        self.consecutive_failures = 0  # 重置连续失败计数
        self.total_execution_time += execution_time  # 累加总耗时
        # 计算平均耗时
        self.average_execution_time = self.total_execution_time / self.total_runs
        self.last_run_time = execution_time  # 记录最后执行时间
        self.last_success_time = execution_time  # 记录最后成功时间

    def update_failure(self, execution_time: float) -> None:
        """
        更新失败执行的指标。

        在任务执行失败后调用,更新相关统计数据。

        参数:
            execution_time: 本次执行耗时(秒)
        """
        self.total_runs += 1  # 总次数加1
        self.failed_runs += 1  # 失败次数加1
        self.consecutive_failures += 1  # 连续失败计数加1
        self.total_execution_time += execution_time  # 累加总耗时
        # 计算平均耗时
        self.average_execution_time = self.total_execution_time / self.total_runs
        self.last_run_time = execution_time  # 记录最后执行时间
        self.last_failure_time = execution_time  # 记录最后失败时间
