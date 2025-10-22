"""重试机制测试。"""

import pytest

from chronflow.retry import RetryPolicy, RetryStrategy


class TestRetryPolicy:
    """重试策略测试类。"""

    def test_default_policy(self):
        """测试默认重试策略。"""
        policy = RetryPolicy.default()

        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL
        assert policy.wait_min == 1.0
        assert policy.wait_max == 60.0
        assert policy.multiplier == 2.0
        assert policy.reraise is True

    def test_no_retry_policy(self):
        """测试无重试策略。"""
        policy = RetryPolicy.no_retry()

        assert policy.max_attempts == 1
        assert policy.strategy == RetryStrategy.NONE

    def test_aggressive_policy(self):
        """测试激进重试策略。"""
        policy = RetryPolicy.aggressive()

        assert policy.max_attempts == 10
        assert policy.strategy == RetryStrategy.EXPONENTIAL
        assert policy.wait_min == 0.5
        assert policy.wait_max == 120.0
        assert policy.multiplier == 2.5

    def test_custom_policy(self):
        """测试自定义策略。"""
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.FIXED,
            wait_min=2.0,
            wait_max=30.0,
        )

        assert policy.max_attempts == 5
        assert policy.strategy == RetryStrategy.FIXED
        assert policy.wait_min == 2.0
        assert policy.wait_max == 30.0

    def test_create_retryer_exponential(self):
        """测试创建指数退避重试器。"""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
        )

        retryer = policy.create_retryer()
        assert retryer is not None

    def test_create_retryer_fixed(self):
        """测试创建固定间隔重试器。"""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED,
            wait_min=1.0,
        )

        retryer = policy.create_retryer()
        assert retryer is not None

    def test_create_retryer_random(self):
        """测试创建随机间隔重试器。"""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.RANDOM,
            wait_min=1.0,
            wait_max=5.0,
        )

        retryer = policy.create_retryer()
        assert retryer is not None

    def test_create_retryer_none(self):
        """测试创建无重试策略重试器。"""
        policy = RetryPolicy(
            max_attempts=1,
            strategy=RetryStrategy.NONE,
        )

        retryer = policy.create_retryer()
        assert retryer is not None

    def test_validation_max_attempts(self):
        """测试最大尝试次数验证。"""
        with pytest.raises(ValueError):
            RetryPolicy(max_attempts=0)

        with pytest.raises(ValueError):
            RetryPolicy(max_attempts=101)

    def test_validation_wait_times(self):
        """测试等待时间验证。"""
        with pytest.raises(ValueError):
            RetryPolicy(wait_min=-1.0)

        with pytest.raises(ValueError):
            RetryPolicy(wait_max=-1.0)

    def test_validation_multiplier(self):
        """测试倍数验证。"""
        with pytest.raises(ValueError):
            RetryPolicy(multiplier=0.5)


class TestRetryStrategy:
    """重试策略枚举测试。"""

    def test_strategy_values(self):
        """测试策略枚举值。"""
        assert RetryStrategy.EXPONENTIAL == "exponential"
        assert RetryStrategy.FIXED == "fixed"
        assert RetryStrategy.RANDOM == "random"
        assert RetryStrategy.NONE == "none"

    def test_strategy_from_string(self):
        """测试从字符串创建策略。"""
        assert RetryStrategy("exponential") == RetryStrategy.EXPONENTIAL
        assert RetryStrategy("fixed") == RetryStrategy.FIXED
        assert RetryStrategy("random") == RetryStrategy.RANDOM
        assert RetryStrategy("none") == RetryStrategy.NONE
