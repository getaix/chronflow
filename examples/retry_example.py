"""重试机制示例 - 演示任务失败时的重试策略。"""

import asyncio
import random

from chronflow import RetryPolicy, Scheduler, interval

scheduler = Scheduler()

# 用于演示的失败计数器
fail_count = {"unstable_task": 0, "critical_task": 0}


@interval(
    10,
    retry_policy=RetryPolicy(
        max_attempts=3,
        strategy="exponential",  # 指数退避
        wait_min=1.0,
        wait_max=10.0,
        multiplier=2.0,
    ),
)
async def unstable_task():
    """不稳定的任务 - 模拟随机失败。"""
    fail_count["unstable_task"] += 1

    # 30% 概率失败
    if random.random() < 0.3:
        raise Exception("模拟网络错误")



@interval(
    15,
    retry_policy=RetryPolicy.aggressive(),  # 使用预设的激进重试策略
    timeout=5.0,  # 5秒超时
)
async def critical_task():
    """关键任务 - 使用激进重试策略。"""
    fail_count["critical_task"] += 1

    # 模拟耗时操作
    delay = random.uniform(1, 3)
    await asyncio.sleep(delay)

    # 前2次必定失败,演示重试
    if fail_count["critical_task"] <= 2:
        raise Exception("模拟数据库连接失败")


    # 重置计数器
    fail_count["critical_task"] = 0


@interval(
    8,
    retry_policy=RetryPolicy.no_retry(),  # 不重试
)
async def no_retry_task():
    """不重试的任务 - 失败即停止。"""
    # 50% 概率失败
    if random.random() < 0.5:
        raise Exception("立即失败")



@interval(20)
async def show_metrics():
    """显示任务指标。"""

    for task_name in ["unstable_task", "critical_task", "no_retry_task"]:
        task = scheduler.get_task(task_name)
        if task:
            metrics = task.metrics
            (
                (metrics.successful_runs / metrics.total_runs * 100)
                if metrics.total_runs > 0
                else 0
            )

            if metrics.average_execution_time > 0:
                pass



async def main():
    """主函数。"""

    try:
        await scheduler.start(daemon=True)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
