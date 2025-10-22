"""配置模块测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from fscheduler.config import SchedulerConfig, TaskMetrics


class TestSchedulerConfig:
    """调度器配置测试类。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = SchedulerConfig()

        assert config.max_workers == 10
        assert config.queue_size == 1000
        assert config.shutdown_timeout == 30.0
        assert config.enable_logging is True
        assert config.log_level == "INFO"
        assert config.timezone == "UTC"
        assert config.persistence_enabled is False

    def test_custom_config(self):
        """测试自定义配置。"""
        config = SchedulerConfig(
            max_workers=20,
            queue_size=5000,
            log_level="DEBUG",
            timezone="Asia/Shanghai",
        )

        assert config.max_workers == 20
        assert config.queue_size == 5000
        assert config.log_level == "DEBUG"
        assert config.timezone == "Asia/Shanghai"

    def test_invalid_timezone(self):
        """测试无效时区。"""
        with pytest.raises(ValueError, match="无效的时区"):
            SchedulerConfig(timezone="Invalid/Timezone")

    def test_from_json_file(self):
        """测试从 JSON 文件加载配置。"""
        config_data = {
            "max_workers": 15,
            "queue_size": 2000,
            "log_level": "WARNING",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = SchedulerConfig.from_file(temp_path)
            assert config.max_workers == 15
            assert config.queue_size == 2000
            assert config.log_level == "WARNING"
        finally:
            Path(temp_path).unlink()

    def test_from_toml_file(self):
        """测试从 TOML 文件加载配置。"""
        config_content = """
max_workers = 25
queue_size = 3000
log_level = "ERROR"
timezone = "UTC"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = SchedulerConfig.from_file(temp_path)
            assert config.max_workers == 25
            assert config.queue_size == 3000
            assert config.log_level == "ERROR"
        finally:
            Path(temp_path).unlink()

    def test_file_not_found(self):
        """测试配置文件不存在。"""
        with pytest.raises(FileNotFoundError):
            SchedulerConfig.from_file("nonexistent.json")

    def test_unsupported_format(self):
        """测试不支持的文件格式。"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="不支持的配置文件格式"):
                SchedulerConfig.from_file(temp_path)
        finally:
            Path(temp_path).unlink()


class TestTaskMetrics:
    """任务指标测试类。"""

    def test_initial_metrics(self):
        """测试初始指标。"""
        metrics = TaskMetrics()

        assert metrics.total_runs == 0
        assert metrics.successful_runs == 0
        assert metrics.failed_runs == 0
        assert metrics.total_execution_time == 0.0
        assert metrics.average_execution_time == 0.0
        assert metrics.consecutive_failures == 0

    def test_update_success(self):
        """测试更新成功指标。"""
        metrics = TaskMetrics()

        metrics.update_success(1.5)

        assert metrics.total_runs == 1
        assert metrics.successful_runs == 1
        assert metrics.failed_runs == 0
        assert metrics.total_execution_time == 1.5
        assert metrics.average_execution_time == 1.5
        assert metrics.consecutive_failures == 0
        assert metrics.last_run_time == 1.5
        assert metrics.last_success_time == 1.5

    def test_update_failure(self):
        """测试更新失败指标。"""
        metrics = TaskMetrics()

        metrics.update_failure(2.0)

        assert metrics.total_runs == 1
        assert metrics.successful_runs == 0
        assert metrics.failed_runs == 1
        assert metrics.total_execution_time == 2.0
        assert metrics.average_execution_time == 2.0
        assert metrics.consecutive_failures == 1
        assert metrics.last_run_time == 2.0
        assert metrics.last_failure_time == 2.0

    def test_consecutive_failures(self):
        """测试连续失败计数。"""
        metrics = TaskMetrics()

        metrics.update_failure(1.0)
        metrics.update_failure(1.0)
        metrics.update_failure(1.0)

        assert metrics.consecutive_failures == 3
        assert metrics.failed_runs == 3

        # 成功后重置连续失败
        metrics.update_success(1.0)

        assert metrics.consecutive_failures == 0
        assert metrics.failed_runs == 3
        assert metrics.successful_runs == 1

    def test_average_execution_time(self):
        """测试平均执行时间计算。"""
        metrics = TaskMetrics()

        metrics.update_success(1.0)
        metrics.update_success(2.0)
        metrics.update_success(3.0)

        assert metrics.total_runs == 3
        assert metrics.total_execution_time == 6.0
        assert metrics.average_execution_time == 2.0
