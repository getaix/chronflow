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
            "# HELP chronflow_uptime_seconds Uptime in seconds",
            "# TYPE chronflow_uptime_seconds gauge",
            f"chronflow_uptime_seconds {stats['uptime_seconds']}",
            "",
            "# HELP chronflow_executions_total Total task executions",
            "# TYPE chronflow_executions_total counter",
            f"chronflow_executions_total {stats['total_executions']}",
            "",
            "# HELP chronflow_executions_success Successful executions",
            "# TYPE chronflow_executions_success counter",
            f"chronflow_executions_success {stats['successful_executions']}",
            "",
            "# HELP chronflow_executions_failed Failed executions",
            "# TYPE chronflow_executions_failed counter",
            f"chronflow_executions_failed {stats['failed_executions']}",
            "",
            "# HELP chronflow_duration_seconds_total Total execution duration",
            "# TYPE chronflow_duration_seconds_total counter",
            f"chronflow_duration_seconds_total {stats['total_duration']}",
            "",
            "# HELP chronflow_duration_seconds_average Average execution duration",
            "# TYPE chronflow_duration_seconds_average gauge",
            f"chronflow_duration_seconds_average {stats['average_duration']}",
            "",
        ]

        # 添加每个任务的指标
        for task_name, task_stats in stats["task_stats"].items():
            lines.extend(
                [
                    "# HELP chronflow_task_executions Task executions by name",
                    "# TYPE chronflow_task_executions counter",
                    f'chronflow_task_executions{{task="{task_name}"}} {task_stats["executions"]}',
                    "",
                    "# HELP chronflow_task_duration_seconds Task duration by name",
                    "# TYPE chronflow_task_duration_seconds gauge",
                    f'chronflow_task_duration_seconds{{task="{task_name}",stat="avg"}}'
                    f' {task_stats["average_duration"]}',
                    f'chronflow_task_duration_seconds{{task="{task_name}",stat="min"}}'
                    f' {task_stats["min_duration"]}',
                    f'chronflow_task_duration_seconds{{task="{task_name}",stat="max"}}'
                    f' {task_stats["max_duration"]}',
                    "",
                ]
            )

        return "\n".join(lines)

    def format_table(self, *, show_tasks: bool = True, max_tasks: int = 20) -> str:
        """格式化指标为美观的表格展示。

        参数:
            show_tasks: 是否显示任务级别统计
            max_tasks: 最多显示的任务数量

        返回值:
            格式化的表格字符串

        示例:
            ```python
            print(collector.format_table())
            ```
        """
        stats = self.get_stats()

        # 构建总览表格
        lines = [
            "=" * 70,
            "Chronflow 调度器指标总览".center(70),
            "=" * 70,
            "",
            f"{'运行时间:':<20} {self._format_duration(stats['uptime_seconds'])}",
            f"{'总执行次数:':<20} {stats['total_executions']:,}",
            f"{'成功:':<20} {stats['successful_executions']:,}",
            f"{'失败:':<20} {stats['failed_executions']:,}",
            f"{'成功率:':<20} {stats['success_rate'] * 100:.2f}%",
            f"{'平均执行时长:':<20} {stats['average_duration']:.4f}秒",
            f"{'执行速率:':<20} {stats['executions_per_second']:.2f} 次/秒",
            "",
        ]

        # 如果有任务统计且需要显示
        if show_tasks and stats["task_stats"]:
            lines.extend(
                [
                    "=" * 70,
                    "任务执行统计".center(70),
                    "=" * 70,
                    "",
                ]
            )

            # 表头
            header = (
                f"{'任务名':<20} {'次数':>8} {'成功':>8} {'失败':>8} "
                f"{'成功率':>8} {'平均时长':>12}"
            )
            lines.append(header)
            lines.append("-" * 70)

            # 按执行次数排序任务
            sorted_tasks = sorted(
                stats["task_stats"].items(),
                key=lambda x: x[1]["executions"],
                reverse=True,
            )[:max_tasks]

            # 任务行
            for task_name, task_stats in sorted_tasks:
                # 截断过长的任务名
                display_name = (
                    task_name[:17] + "..." if len(task_name) > 20 else task_name
                )

                lines.append(
                    f"{display_name:<20} "
                    f"{task_stats['executions']:>8,} "
                    f"{task_stats['successes']:>8,} "
                    f"{task_stats['failures']:>8,} "
                    f"{task_stats['success_rate'] * 100:>7.1f}% "
                    f"{task_stats['average_duration']:>11.4f}秒"
                )

            if len(stats["task_stats"]) > max_tasks:
                lines.append(
                    f"... 还有 {len(stats['task_stats']) - max_tasks} 个任务未显示"
                )

        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def format_task_detail(self, task_name: str) -> str:
        """格式化单个任务的详细统计。

        参数:
            task_name: 任务名称

        返回值:
            格式化的详细统计字符串

        抛出:
            KeyError: 任务不存在
        """
        if task_name not in self.task_stats:
            raise KeyError(f"任务 '{task_name}' 不存在")

        stats = self.task_stats[task_name]
        avg_duration = (
            stats["total_duration"] / stats["executions"]
            if stats["executions"] > 0
            else 0.0
        )
        success_rate = (
            stats["successes"] / stats["executions"] if stats["executions"] > 0 else 0.0
        )

        lines = [
            "=" * 60,
            f"任务 '{task_name}' 详细统计".center(60),
            "=" * 60,
            "",
            f"{'总执行次数:':<20} {stats['executions']:,}",
            f"{'成功次数:':<20} {stats['successes']:,}",
            f"{'失败次数:':<20} {stats['failures']:,}",
            f"{'成功率:':<20} {success_rate * 100:.2f}%",
            "",
            f"{'总执行时长:':<20} {self._format_duration(stats['total_duration'])}",
            f"{'平均时长:':<20} {avg_duration:.4f}秒",
            f"{'最短时长:':<20} {stats['min_duration']:.4f}秒",
            f"{'最长时长:':<20} {stats['max_duration']:.4f}秒",
            "",
            "=" * 60,
            "",
        ]

        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """格式化时长为人类可读形式。

        参数:
            seconds: 秒数

        返回值:
            格式化的时长字符串
        """
        if seconds < 60:
            return f"{seconds:.2f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f}分钟"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.2f}小时"
        else:
            days = seconds / 86400
            return f"{days:.2f}天"

    def reset(self) -> None:
        """重置所有统计信息。"""
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_duration = 0.0
        self.task_stats.clear()
        self.start_time = datetime.now()
