"""
配置模型和解析模块。

本模块提供:
- SchedulerConfig: 调度器配置类,支持环境变量和文件配置
- TaskMetrics: 任务执行指标类,用于统计任务运行情况
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from chronflow.backends import QueueBackend


class BackendConfig(BaseModel):
    """队列后端配置模型,用于声明式描述后端类型和初始化参数。

    本配置类封装了后端实例化的所有信息,支持以下几种声明方式:
    - 字符串: 仅指定后端名称,使用默认参数
    - 字典: 同时指定后端名称和构造参数
    - 对象: 直接传入 BackendConfig 实例

    配置示例:
        ```python
        # 方式1: 使用默认内存后端
        config = BackendConfig()

        # 方式2: 指定后端名称
        config = BackendConfig(name="sqlite")

        # 方式3: 指定后端名称和参数
        config = BackendConfig(
            name="redis",
            options={"host": "localhost", "port": 6379}
        )

        # 方式4: 从字典创建(会自动转换)
        data = {"name": "memory", "options": {"max_size": 1000}}
        config = BackendConfig(**data)

        # 实例化后端
        backend = config.instantiate()
        ```

    属性:
        name: 已注册的后端名称(如 memory、redis、rabbitmq、sqlite)
        options: 传递给后端构造函数的参数字典

    注意:
        - 后端名称必须已通过 ``register_backend`` 注册
        - options 中的参数取决于具体后端的构造函数签名
        - 内存后端会自动继承调度器的 queue_size 配置(如未显式指定)
    """

    name: str = Field(
        default="memory",
        description="后端名称,对应已注册的 backend 标识(如 memory、redis、rabbitmq、sqlite)",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="后端构造参数,会在实例化时传递给具体后端实现",
    )

    def instantiate(self, *, default_queue_size: int | None = None) -> "QueueBackend":
        """根据配置实例化对应的队列后端。

        自动将配置中的参数传递给后端工厂,并处理特殊逻辑(如内存后端的默认队列大小)。

        参数:
            default_queue_size: 默认队列大小,仅当后端为 memory 且未显式指定 max_size 时生效

        返回值:
            实例化的 QueueBackend 对象

        异常:
            ValueError: 如果后端名称未注册
            ImportError: 如果后端依赖缺失(如 Redis/RabbitMQ)
            TypeError: 如果 options 中的参数与后端构造函数不匹配

        实例化流程:
        1. 复制 options 字典避免修改原始配置
        2. 如果是内存后端且未指定 max_size,使用 default_queue_size
        3. 调用 create_backend 创建后端实例

        示例:
            ```python
            config = BackendConfig(name="memory")
            backend = config.instantiate(default_queue_size=5000)
            # 内存后端会使用 max_size=5000

            config = BackendConfig(name="memory", options={"max_size": 1000})
            backend = config.instantiate(default_queue_size=5000)
            # 内存后端会使用 max_size=1000(显式指定优先)
            ```
        """
        from chronflow.backends import create_backend

        kwargs = dict(self.options)

        # 特殊处理: 内存后端自动继承默认队列大小
        if (
            default_queue_size is not None
            and self.name.strip().lower() == "memory"
            and "max_size" not in kwargs
        ):
            kwargs["max_size"] = default_queue_size

        return create_backend(self.name, **kwargs)


class SchedulerConfig(BaseSettings):
    """
    调度器主配置类。

    支持从以下来源加载配置(优先级从高到低):
    1. 直接传入的参数
    2. 环境变量(前缀 chronflow_)
    3. .env 文件
    4. 默认值

    示例:
        # 使用默认配置
        config = SchedulerConfig()

        # 自定义配置
        config = SchedulerConfig(max_workers=20, log_level="DEBUG")

        # 从环境变量(chronflow_MAX_WORKERS=20)
        config = SchedulerConfig()
    """

    model_config = SettingsConfigDict(
        env_prefix="chronflow_",  # 环境变量前缀
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

    schedule_check_interval: float = Field(
        default=1.0,
        gt=0,
        le=60.0,
        description="调度循环检查间隔(秒),控制任务调度的频率",
    )

    enable_logging: bool = Field(
        default=True,
        description="是否启用日志记录,设为 False 可完全禁用日志输出",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别,控制输出的日志详细程度",
    )

    log_task_success: bool = Field(
        default=False,
        description="是否以 info 级别输出任务成功日志,默认仅输出 debug 以避免刷屏",
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
        default=Path(".chronflow_state.json"),
        description="持久化文件路径,用于保存调度器状态",
    )
    backend: BackendConfig = Field(
        default_factory=BackendConfig,
        description="队列后端配置,默认使用内存后端",
    )
    pid_file: Path = Field(
        default=Path("~/.chronflow/chronflow.pid"),
        description="守护进程 PID 文件路径",
    )
    process_name: str = Field(
        default="chronflow-scheduler",
        description="守护进程标识名称",
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

    @field_validator("backend", mode="before")
    @classmethod
    def parse_backend(cls, value: Any) -> BackendConfig:
        """允许以字符串或映射形式声明队列后端。"""
        if value is None or value == "":
            return BackendConfig()

        if isinstance(value, BackendConfig):
            return value

        if isinstance(value, str):
            return BackendConfig(name=value)

        if isinstance(value, dict):
            data = dict(value)
            if "name" not in data and "type" in data:
                data["name"] = data.pop("type")
            return BackendConfig(**data)

        raise ValueError("backend 配置必须是字符串、映射或 BackendConfig 实例")

    @field_validator("backend", mode="after")
    @classmethod
    def validate_backend_exists(cls, value: BackendConfig) -> BackendConfig:
        """验证后端是否已注册。

        此验证在配置加载时立即执行,避免运行时错误。
        """
        from chronflow.backends import get_registered_backends

        registered = get_registered_backends()
        if value.name not in registered:
            available = ", ".join(sorted(registered))
            raise ValueError(
                f"未注册的后端 '{value.name}'。\n"
                f"可用后端: {available}\n"
                f"提示: 使用 register_backend() 注册自定义后端"
            )

        return value

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

    def create_backend(self) -> "QueueBackend":
        """根据配置生成队列后端实例。"""
        return self.backend.instantiate(default_queue_size=self.queue_size)


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
