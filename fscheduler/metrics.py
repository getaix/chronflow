"""性能监控和指标导出模块。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricsCollector:
    """指标收集器,用于收集调度器性能指标。

    示例:
        ```python
        collector = MetricsCollector()

        # 记录任务执行
        collector.record_task_execution("my_task", success=True, duration=1.5)

        # 获取统计信息
        stats = collector.get_stats()
        print(f"总执行次数: {stats['total_executions']}")
        ```
    """

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration: float = 0.0
    task_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)

    def record_task_execution(
        self, task_name: str, success: bool, duration: float
    ) -> None:
        """记录任务执行。

        参数:
            task_name: 任务名称
            success: 是否成功
            duration: 执行时长(秒)
        """
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        self.total_duration += duration

        # 更新任务级别统计
        if task_name not in self.task_stats:
            self.task_stats[task_name] = {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
            }

        stats = self.task_stats[task_name]
        stats["executions"] += 1
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        stats["total_duration"] += duration
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息。

        返回值:
            包含所有统计信息的字典
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        avg_duration = (
            self.total_duration / self.total_executions
            if self.total_executions > 0
            else 0.0
        )

        return {
            "uptime_seconds": uptime,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0
                else 0.0
            ),
            "total_duration": self.total_duration,
            "average_duration": avg_duration,
            "executions_per_second": (
                self.total_executions / uptime if uptime > 0 else 0.0
            ),
            "task_stats": {
                name: {
                    **stats,
                    "average_duration": (
                        stats["total_duration"] / stats["executions"]
                        if stats["executions"] > 0
                        else 0.0
                    ),
                    "success_rate": (
                        stats["successes"] / stats["executions"]
                        if stats["executions"] > 0
                        else 0.0
                    ),
                }
                for name, stats in self.task_stats.items()
            },
        }

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式的指标。

        返回值:
            Prometheus 格式的指标文本

        示例:
            ```python
            metrics_text = collector.export_prometheus()
            # 可以通过 HTTP 端点暴露给 Prometheus
            ```
        """
        stats = self.get_stats()
        lines = [
            "# HELP fscheduler_uptime_seconds Uptime in seconds",
            "# TYPE fscheduler_uptime_seconds gauge",
            f"fscheduler_uptime_seconds {stats['uptime_seconds']}",
            "",
            "# HELP fscheduler_executions_total Total task executions",
            "# TYPE fscheduler_executions_total counter",
            f"fscheduler_executions_total {stats['total_executions']}",
            "",
            "# HELP fscheduler_executions_success Successful executions",
            "# TYPE fscheduler_executions_success counter",
            f"fscheduler_executions_success {stats['successful_executions']}",
            "",
            "# HELP fscheduler_executions_failed Failed executions",
            "# TYPE fscheduler_executions_failed counter",
            f"fscheduler_executions_failed {stats['failed_executions']}",
            "",
            "# HELP fscheduler_duration_seconds_total Total execution duration",
            "# TYPE fscheduler_duration_seconds_total counter",
            f"fscheduler_duration_seconds_total {stats['total_duration']}",
            "",
            "# HELP fscheduler_duration_seconds_average Average execution duration",
            "# TYPE fscheduler_duration_seconds_average gauge",
            f"fscheduler_duration_seconds_average {stats['average_duration']}",
            "",
        ]

        # 添加每个任务的指标
        for task_name, task_stats in stats["task_stats"].items():
            lines.extend(
                [
                    "# HELP fscheduler_task_executions Task executions by name",
                    "# TYPE fscheduler_task_executions counter",
                    f'fscheduler_task_executions{{task="{task_name}"}} {task_stats["executions"]}',
                    "",
                    "# HELP fscheduler_task_duration_seconds Task duration by name",
                    "# TYPE fscheduler_task_duration_seconds gauge",
                    f'fscheduler_task_duration_seconds{{task="{task_name}",stat="avg"}}'
                    f' {task_stats["average_duration"]}',
                    f'fscheduler_task_duration_seconds{{task="{task_name}",stat="min"}}'
                    f' {task_stats["min_duration"]}',
                    f'fscheduler_task_duration_seconds{{task="{task_name}",stat="max"}}'
                    f' {task_stats["max_duration"]}',
                    "",
                ]
            )

        return "\n".join(lines)

    def reset(self) -> None:
        """重置所有统计信息。"""
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_duration = 0.0
        self.task_stats.clear()
        self.start_time = datetime.now()
