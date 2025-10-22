"""性能指标收集示例。

演示如何使用 MetricsCollector 监控任务执行性能,并导出 Prometheus 格式的指标。
"""

import asyncio
from datetime import datetime

from chronflow import Scheduler
from chronflow.decorators import interval
from chronflow.task import Task, TaskConfig, ScheduleType


# 示例 1: 启用指标收集的调度器
async def example_with_metrics():
    """启用性能指标收集。"""
    # 创建启用指标的调度器
    scheduler = Scheduler(enable_metrics=True)

    # 定义一个简单任务
    @interval(seconds=1)
    async def my_task():
        """每秒执行一次的任务。"""
        await asyncio.sleep(0.1)
        print("Task executed!")  # noqa: T201

    # 注册任务
    scheduler.register_task(my_task.__chronflow_task__)

    # 启动调度器(运行 5 秒)
    async with scheduler.run_context():
        await asyncio.sleep(5)

    # 获取性能指标
    metrics = scheduler.get_metrics()
    if metrics:
        print("\n=== 性能指标 ===")  # noqa: T201
        print(f"总执行次数: {metrics['total_executions']}")  # noqa: T201
        print(f"成功次数: {metrics['successful_executions']}")  # noqa: T201
        print(f"失败次数: {metrics['failed_executions']}")  # noqa: T201
        print(f"成功率: {metrics['success_rate']:.2%}")  # noqa: T201
        print(f"平均执行时间: {metrics['average_duration']:.3f}秒")  # noqa: T201
        print(f"运行时长: {metrics['uptime_seconds']:.1f}秒")  # noqa: T201

        # 查看各任务的详细统计
        print("\n=== 任务详细统计 ===")  # noqa: T201
        for task_name, stats in metrics["task_stats"].items():
            print(f"\n任务: {task_name}")  # noqa: T201
            print(f"  执行次数: {stats['executions']}")  # noqa: T201
            print(f"  成功次数: {stats['successes']}")  # noqa: T201
            print(f"  失败次数: {stats['failures']}")  # noqa: T201
            print(f"  成功率: {stats['success_rate']:.2%}")  # noqa: T201
            print(f"  平均时长: {stats['average_duration']:.3f}秒")  # noqa: T201
            print(f"  最小时长: {stats['min_duration']:.3f}秒")  # noqa: T201
            print(f"  最大时长: {stats['max_duration']:.3f}秒")  # noqa: T201


# 示例 2: 导出 Prometheus 格式的指标
async def example_prometheus_export():
    """导出 Prometheus 格式的指标。"""
    scheduler = Scheduler(enable_metrics=True)

    # 定义一个任务
    config = TaskConfig(
        name="prometheus_task",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=1,
        start_time=datetime.now(),
    )

    async def task_func():
        await asyncio.sleep(0.05)
        return "done"

    task = Task(func=task_func, config=config)
    scheduler.register_task(task)

    # 运行一段时间
    async with scheduler.run_context():
        await asyncio.sleep(3)

    # 导出 Prometheus 格式
    prometheus_metrics = scheduler.export_prometheus_metrics()
    if prometheus_metrics:
        print("\n=== Prometheus 指标 ===")  # noqa: T201
        print(prometheus_metrics)  # noqa: T201


# 示例 3: 监控失败任务
async def example_monitor_failures():
    """监控任务失败情况。"""
    scheduler = Scheduler(enable_metrics=True)

    # 定义一个会失败的任务
    @interval(seconds=1)
    async def failing_task():
        """会随机失败的任务。"""
        import random  # noqa: PLC0415

        if random.random() < 0.3:  # 30% 失败率
            raise ValueError("Random failure!")
        return "success"

    scheduler.register_task(failing_task.__chronflow_task__)

    # 运行一段时间
    async with scheduler.run_context():
        await asyncio.sleep(10)

    # 查看失败统计
    metrics = scheduler.get_metrics()
    if metrics:
        print("\n=== 失败监控 ===")  # noqa: T201
        print(f"总执行: {metrics['total_executions']}")  # noqa: T201
        print(f"成功: {metrics['successful_executions']}")  # noqa: T201
        print(f"失败: {metrics['failed_executions']}")  # noqa: T201
        print(f"失败率: {(1 - metrics['success_rate']):.2%}")  # noqa: T201


# 示例 4: 重置指标
async def example_reset_metrics():
    """演示如何重置性能指标。"""
    scheduler = Scheduler(enable_metrics=True)

    # 手动记录一些指标
    scheduler.metrics_collector.record_task_execution(
        task_name="test_task",
        success=True,
        duration=1.0,
    )
    scheduler.metrics_collector.record_task_execution(
        task_name="test_task",
        success=False,
        duration=0.5,
    )

    # 查看指标
    metrics_before = scheduler.get_metrics()
    print("重置前:")  # noqa: T201
    print(f"  总执行: {metrics_before['total_executions']}")  # noqa: T201

    # 重置指标
    scheduler.reset_metrics()

    # 再次查看
    metrics_after = scheduler.get_metrics()
    print("重置后:")  # noqa: T201
    print(f"  总执行: {metrics_after['total_executions']}")  # noqa: T201


# 示例 5: 暴露指标给 Prometheus
async def example_prometheus_endpoint():
    """演示如何通过 HTTP 端点暴露 Prometheus 指标。

    注意: 需要安装 aiohttp: pip install aiohttp
    """
    try:
        from aiohttp import web  # noqa: PLC0415
    except ImportError:
        print("此示例需要 aiohttp,请运行: pip install aiohttp")  # noqa: T201
        return

    scheduler = Scheduler(enable_metrics=True)

    # 定义一个任务
    @interval(seconds=2)
    async def monitored_task():
        """被监控的任务。"""
        await asyncio.sleep(0.1)
        return "ok"

    scheduler.register_task(monitored_task.__chronflow_task__)

    # 定义 HTTP 处理器
    async def metrics_handler(request):
        """返回 Prometheus 格式的指标。"""
        metrics_text = scheduler.export_prometheus_metrics()
        return web.Response(text=metrics_text or "", content_type="text/plain")

    # 创建 web 应用
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)

    # 启动 HTTP 服务器和调度器
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 9090)

    print("Prometheus 指标端点: http://localhost:9090/metrics")  # noqa: T201
    print("按 Ctrl+C 停止...")  # noqa: T201

    try:
        # 启动 HTTP 服务器
        await site.start()

        # 启动调度器
        async with scheduler.run_context():
            await asyncio.sleep(30)  # 运行 30 秒

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    # 运行示例
    print("=== 示例 1: 基本指标收集 ===")  # noqa: T201
    asyncio.run(example_with_metrics())

    print("\n=== 示例 2: Prometheus 格式导出 ===")  # noqa: T201
    asyncio.run(example_prometheus_export())

    print("\n=== 示例 3: 监控失败 ===")  # noqa: T201
    asyncio.run(example_monitor_failures())

    print("\n=== 示例 4: 重置指标 ===")  # noqa: T201
    asyncio.run(example_reset_metrics())

    # 可选: 运行 Prometheus 端点示例
    # asyncio.run(example_prometheus_endpoint())
