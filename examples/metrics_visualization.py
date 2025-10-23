"""Metrics 可视化示例。

演示如何使用 MetricsCollector 的表格展示功能。
"""

import asyncio

from chronflow import Scheduler, SchedulerConfig
from chronflow.decorators import interval, set_global_scheduler
from chronflow.metrics import MetricsCollector


# 创建指标收集器
collector = MetricsCollector()


# 使用装饰器定义任务
@interval(1)
async def fast_task():
    """快速任务"""
    await asyncio.sleep(0.01)


@interval(2)
async def medium_task():
    """中等速度任务"""
    await asyncio.sleep(0.05)


@interval(3)
async def slow_task():
    """慢速任务"""
    await asyncio.sleep(0.1)


async def main():
    # 创建调度器配置
    config = SchedulerConfig(
        max_workers=5,
        enable_logging=True,
        log_level="INFO",
    )
    scheduler = Scheduler(config)

    # 设置全局调度器,自动注册装饰器任务
    set_global_scheduler(scheduler)

    # 启动调度器
    start_task = asyncio.create_task(scheduler.start())

    # 运行15秒
    await asyncio.sleep(15)

    # 停止调度器
    await scheduler.stop()
    await start_task

    # 收集指标
    stats = await scheduler.get_stats()
    for task_data in stats["tasks"]:
        task_name = task_data["name"]
        metrics = task_data["metrics"]

        # 记录每次成功运行
        for _ in range(metrics["successful_runs"]):
            collector.record_task_execution(
                task_name=task_name,
                success=True,
                duration=metrics["average_execution_time"] or 0.0,
            )

        # 记录每次失败运行
        for _ in range(metrics["failed_runs"]):
            collector.record_task_execution(
                task_name=task_name,
                success=False,
                duration=metrics["average_execution_time"] or 0.0,
            )

    # 显示表格格式的指标
    print("\n" + "=" * 70)
    print("方式1: 完整表格展示".center(70))
    print("=" * 70)
    print(collector.format_table())

    # 显示单个任务详情
    print("\n" + "=" * 70)
    print("方式2: 单任务详细统计".center(70))
    print("=" * 70)
    if "fast_task" in collector.task_stats:
        print(collector.format_task_detail("fast_task"))

    # 显示 JSON 格式
    print("\n" + "=" * 70)
    print("方式3: JSON 格式".center(70))
    print("=" * 70)
    import json

    print(json.dumps(collector.get_stats(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
