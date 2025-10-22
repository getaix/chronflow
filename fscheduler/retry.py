"""失败任务的重试机制。"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    wait_random,
)


class RetryStrategy(str, Enum):
    """重试策略类型。"""

    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    RANDOM = "random"
    NONE = "none"


class RetryPolicy(BaseModel):
    """任务重试行为的配置。"""

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=100,
        description="最大重试次数",
    )

    strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL,
        description="使用的重试策略",
    )

    wait_min: float = Field(
        default=1.0,
        ge=0.0,
        description="重试间的最小等待时间(秒)",
    )

    wait_max: float = Field(
        default=60.0,
        ge=0.0,
        description="重试间的最大等待时间(秒)",
    )

    multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="指数退避的倍率",
    )

    retry_exceptions: tuple[type[Exception], ...] = Field(
        default=(Exception,),
        description="触发重试的异常类型",
    )

    reraise: bool = Field(
        default=True,
        description="达到最大重试后是否重新抛出异常",
    )

    model_config = {"arbitrary_types_allowed": True}

    def create_retryer(self) -> AsyncRetrying:
        """创建一个 tenacity 的 AsyncRetrying 实例。"""
        # 选择等待策略
        if self.strategy == RetryStrategy.EXPONENTIAL:
            wait_strategy = wait_exponential(
                multiplier=self.multiplier,
                min=self.wait_min,
                max=self.wait_max,
            )
        elif self.strategy == RetryStrategy.FIXED:
            wait_strategy = wait_fixed(self.wait_min)
        elif self.strategy == RetryStrategy.RANDOM:
            wait_strategy = wait_random(min=self.wait_min, max=self.wait_max)
        else:  # NONE
            wait_strategy = wait_fixed(0)

        return AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(self.retry_exceptions),
            reraise=self.reraise,
        )

    @staticmethod
    def no_retry() -> RetryPolicy:
        """创建不重试策略。"""
        return RetryPolicy(max_attempts=1, strategy=RetryStrategy.NONE)

    @staticmethod
    def default() -> RetryPolicy:
        """创建默认重试策略。"""
        return RetryPolicy()

    @staticmethod
    def aggressive() -> RetryPolicy:
        """创建更激进的重试策略,包含更多尝试次数。"""
        return RetryPolicy(
            max_attempts=10,
            strategy=RetryStrategy.EXPONENTIAL,
            wait_min=0.5,
            wait_max=120.0,
            multiplier=2.5,
        )
