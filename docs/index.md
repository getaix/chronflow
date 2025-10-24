# 概览

chronflow 是一个高性能的 Python 异步定时任务调度库，专为 Python 3.11+ 设计。它提供了简洁的装饰器 API、多种队列后端支持、智能重试机制以及完整的类型安全保障。

[![版本](https://img.shields.io/badge/version-0.2.1-blue.svg)](https://github.com/getaix/chronflow/releases/tag/v0.2.1)
[![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![测试覆盖率](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](./changelog.md#021---2025-10-24)
[![许可证](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/getaix/chronflow/blob/main/LICENSE)

- 基于 asyncio 的原生异步支持，高并发、低延迟
- 支持秒级 Cron 表达式定时任务
- 可插拔的队列后端：内存、SQLite、Redis、RabbitMQ
- 智能重试机制，支持指数退避、固定间隔等策略
- 完整的类型提示，IDE 友好
- 零依赖启动，可选外部服务支持

!!! info "最新版本: v0.2.1"
    2025-10-24 发布 - 修复信号处理、日志系统、任务重复执行等关键问题 | [查看更新日志](./changelog.md#021-2025-10-24)

> 环境要求：Python >= 3.11

更多快速示例可参考仓库中的 `examples/` 目录。

## 核心特性

### 高性能异步
基于 Python asyncio，原生异步支持，无同步转异步开销。支持高并发任务执行，吞吐量可达 10000+ tasks/s。

### 秒级精度
支持标准 Cron 表达式并扩展到秒级精度，满足各种定时任务需求。

### 多种后端
- **Memory** - 零依赖，开箱即用
- **SQLite** - 本地持久化，重启不丢任务
- **Redis** - 分布式部署，高性能
- **RabbitMQ** - 高可靠性消息队列

### 简洁 API
装饰器模式，一行代码定义任务：

```python
@cron("*/5 * * * * *")  # 每5秒执行
async def my_task():
    print("任务执行中...")
```

### 智能重试
内置基于 tenacity 的重试机制，支持多种策略：
- 指数退避（适合网络请求）
- 固定间隔（适合轮询）
- 随机间隔（避免雪崩）

### 类型安全
100% 类型提示覆盖，配合 IDE 提供完整的代码补全和类型检查。

## 快速安装

```bash
# 基础安装（内存/SQLite 后端）
pip install chronflow

# 使用 Redis
pip install chronflow[redis]

# 使用 RabbitMQ
pip install chronflow[rabbitmq]

# 完整安装（所有后端）
pip install chronflow[all]
```

## 5 分钟上手

```python
import asyncio
from chronflow import Scheduler, cron, interval

scheduler = Scheduler()

@cron("*/5 * * * * *")  # 每5秒
async def health_check():
    print("健康检查...")

@interval(60)  # 每60秒
async def sync_data():
    print("同步数据...")

async def main():
    await scheduler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

更多详细示例请查看 [快速开始](quickstart.md) 文档。

## 为什么选择 chronflow？

### vs Celery
- ✅ 更轻量 - 无需 Redis/RabbitMQ 即可运行
- ✅ 更简单 - 装饰器即用，无需额外配置
- ✅ 更快速 - 纯 asyncio，无进程开销
- ✅ 更现代 - Python 3.11+ 新特性

### vs APScheduler
- ✅ 更高性能 - 原生异步，不是同步转异步
- ✅ 更可靠 - 优化的内存管理
- ✅ 更灵活 - 可插拔后端
- ✅ 更好的可观测性 - 内置指标和监控

## 许可证

MIT License
