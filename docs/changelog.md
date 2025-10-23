# 更新日志

本文档记录 chronflow 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2025-10-22

### 新增 ✨

#### 可插拔日志系统
- 添加日志适配器接口 `LoggerAdapter`
- 内置支持 structlog、loguru、Python 标准库 logging
- 可以完全自定义日志实现
- 支持禁用日志输出 (`NoOpAdapter`)
- structlog 从核心依赖变为可选依赖

#### 增强的监控功能
- `list_tasks()` - 获取所有任务详细信息列表
- `get_task_count()` - 获取各状态任务数量统计
- `get_task_by_status()` - 按状态筛选任务
- `get_task_by_tag()` - 按标签筛选任务
- `pause_task()` - 暂停指定任务
- `resume_task()` - 恢复指定任务
- 任务列表包含成功率、平均执行时间等指标

#### 新的便捷装饰器
- `@every()` - 更直观的间隔任务 (`@every(minutes=30)`)
- `@hourly()` - 每小时执行 (`@hourly(minute=30)`)
- `@daily()` - 每天执行 (`@daily(hour=9, minute=30)`)
- `@weekly()` - 每周执行 (`@weekly(day=1, hour=10)`)
- `@monthly()` - 每月执行 (`@monthly(day=1)`)

#### Python 版本支持
- 添加 Python 3.13 官方支持
- 继续支持 Python 3.11 和 3.12

### 改进 🔧

- **依赖优化**: structlog 变为可选依赖,减少默认安装体积
- **类型提示**: 所有新功能都有完整的类型提示
- **文档**: 添加详细的新功能文档和示例
- **日志输出**: 优化日志格式,支持结构化日志

### 示例

- 添加 `examples/advanced_features.py` - 高级功能演示
- 添加 `examples/custom_logger.py` - 自定义日志演示

### 技术细节

#### 日志系统架构

```
LoggerAdapter (抽象基类)
    ├── StructlogAdapter (默认,可选)
    ├── LoguruAdapter (可选)
    ├── StdlibAdapter (内置)
    └── NoOpAdapter (内置)
```

#### 新的装饰器映射

| 装饰器 | 等价 Cron | 说明 |
|--------|----------|------|
| `@hourly()` | `0 0 * * * *` | 每小时整点 |
| `@daily()` | `0 0 0 * * *` | 每天 0:00 |
| `@weekly()` | `0 0 0 * * 0` | 每周日 0:00 |
| `@monthly()` | `0 0 0 1 * *` | 每月 1 号 0:00 |

### 破坏性变更 ⚠️

无。此版本完全向后兼容。

### 已知问题

无。

### 安全性

无安全相关更新。

## [0.2.0] - 2025-10-23

本次发布包含新特性与改进：
- 新增 `chronflow/daemon.py`，支持守护进程运行调度器
- 增强指标采集与可视化示例（`examples/metrics_visualization.py`）
- 完善装饰器与配置映射，提升测试覆盖率
- 支持 Python 3.13（CI 验证），保持类型安全
- 文档与示例更新

### 破坏性变更 ⚠️
无。此版本向后兼容。

### 已知问题
无。

---

## [未发布]

### 计划中的功能

- [ ] Web 管理界面
- [ ] Prometheus 指标导出
- [ ] 任务依赖关系
- [ ] 动态添加/删除任务
- [ ] 分布式锁支持
- [ ] PostgreSQL 后端支持

---

## 版本说明

### [0.1.0] - 首个 Beta 版本

这是 chronflow 的首个公开 Beta 版本,包含以下核心功能:

**核心特性:**
- 高性能异步调度器
- 多种队列后端(内存/SQLite/Redis/RabbitMQ)
- 智能重试机制
- 秒级 Cron 表达式支持
- 装饰器 API
- 完整的类型提示
- 可插拔日志系统
- 丰富的监控功能

**队列后端:**
- MemoryBackend - 内存队列,零依赖
- SQLiteBackend - 本地持久化
- RedisBackend - 分布式队列
- RabbitMQBackend - 高可靠性消息队列

**装饰器:**
- `@scheduled` - 通用调度器
- `@cron` - Cron 表达式
- `@interval` - 固定间隔
- `@once` - 一次性任务
- `@every` - 直观间隔
- `@hourly` - 每小时
- `@daily` - 每天
- `@weekly` - 每周
- `@monthly` - 每月

**监控功能:**
- 任务列表查询
- 状态统计
- 标签筛选
- 任务控制(暂停/恢复)
- 详细指标

**日志支持:**
- Structlog
- Loguru
- Python logging
- 自定义适配器
- 禁用日志

**测试覆盖:**
- 60+ 单元测试
- 高测试覆盖率
- 多个实用示例

---

## 贡献

发现 Bug 或有新功能建议?欢迎[提交 Issue](https://github.com/yourusername/chronflow/issues)!

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
