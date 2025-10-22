# 贡献指南

感谢你对 chronflow 的兴趣！本指南将帮助你了解如何为项目做出贡献。

## 开发环境设置

### 1. Fork 和 Clone

```bash
# Fork 项目到你的 GitHub 账号
# 然后 clone 到本地
git clone https://github.com/your-username/chronflow.git
cd chronflow

# 添加上游仓库
git remote add upstream https://github.com/getaix/chronflow.git
```

### 2. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 安装依赖

```bash
# 创建虚拟环境并安装所有依赖
uv sync --all-groups --extra all
```

### 4. 安装开发钩子

```bash
# 安装 pre-commit hooks（可选）
uv run pre-commit install
```

## 开发流程

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 编写代码

- 遵循现有的代码风格
- 添加必要的类型提示
- 编写中文注释和文档字符串
- 确保代码通过所有测试

### 3. 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=chronflow --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 4. 代码检查

```bash
# Ruff 检查
uv run ruff check chronflow/

# Ruff 格式化检查
uv run ruff format --check chronflow/

# 自动修复
uv run ruff check --fix chronflow/
uv run ruff format chronflow/

# 类型检查
uv run mypy chronflow/
```

### 5. 提交代码

```bash
# 添加更改
git add .

# 提交（使用有意义的提交信息）
git commit -m "feat: 添加新功能 XXX"
# 或
git commit -m "fix: 修复 XXX 问题"
```

提交信息格式：
- `feat:` - 新功能
- `fix:` - 修复 bug
- `docs:` - 文档更新
- `test:` - 测试相关
- `refactor:` - 重构代码
- `chore:` - 构建/工具相关

### 6. 推送并创建 PR

```bash
# 推送到你的 fork
git push origin feature/your-feature-name

# 然后在 GitHub 上创建 Pull Request
```

## 代码规范

### Python 代码

- 使用 Python 3.11+ 语法
- 100% 类型提示覆盖
- 遵循 PEP 8 规范
- 行长度限制：100 字符

### 注释和文档

- 所有公共 API 必须有文档字符串
- 文档字符串使用中文
- 使用 Google 风格的文档字符串格式

示例：

```python
def my_function(param1: str, param2: int) -> bool:
    """函数简短描述。

    详细说明函数的功能和用途。

    Args:
        param1: 第一个参数的说明
        param2: 第二个参数的说明

    Returns:
        返回值的说明

    Raises:
        ValueError: 何时抛出此异常

    示例:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    pass
```

### 测试

- 所有新功能必须包含测试
- 测试覆盖率应保持在 80% 以上
- 使用 pytest 和 pytest-asyncio
- 测试函数名使用中文描述

示例：

```python
import pytest
from chronflow import Scheduler

class TestScheduler:
    """调度器测试类。"""

    def test_scheduler_creation(self):
        """测试调度器创建。"""
        scheduler = Scheduler()
        assert scheduler is not None

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """测试调度器启动和停止。"""
        scheduler = Scheduler()
        # 测试逻辑
```

## 文档编写

### 本地预览文档

```bash
# 安装文档依赖
uv pip install -e '.[docs]'

# 启动文档服务器
uv run mkdocs serve

# 浏览器访问 http://127.0.0.1:8000
```

### 构建文档

```bash
uv run mkdocs build
```

### 文档结构

```
docs/
├── index.md                 # 概览页面
├── quickstart.md            # 快速开始
├── guides/                  # 使用指南
│   ├── logging.md
│   ├── monitoring.md
│   └── backends.md
├── api/                     # API 文档
│   ├── scheduler.md
│   ├── task.md
│   └── ...
└── changelog.md             # 更新日志
```

## 发布流程（维护者）

### 1. 更新版本号

编辑 `pyproject.toml`:

```toml
[project]
version = "0.2.0"  # 更新版本号
```

### 2. 更新 CHANGELOG

在 `CHANGELOG.md` 中添加新版本的更新内容。

### 3. 创建标签

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### 4. 自动发布

推送标签后，GitHub Actions 会自动：
- 运行所有测试
- 构建分发包
- 发布到 PyPI

### 5. 手动发布（可选）

```bash
# 构建分发包
uv build

# 检查分发包
twine check dist/*

# 上传到 PyPI
twine upload dist/*
```

## 报告问题

### Bug 报告

创建 Issue 时请包含：

1. **问题描述** - 清晰简洁地描述问题
2. **复现步骤** - 详细的复现步骤
3. **期望行为** - 你期望发生什么
4. **实际行为** - 实际发生了什么
5. **环境信息**:
   - Python 版本
   - chronflow 版本
   - 操作系统
6. **相关日志** - 错误信息、堆栈跟踪等

### 功能请求

创建 Issue 时请说明：

1. **功能描述** - 你希望添加什么功能
2. **使用场景** - 为什么需要这个功能
3. **建议实现** - 你对实现方式的想法（可选）

## 行为准则

- 尊重所有贡献者
- 保持友好和建设性的讨论
- 欢迎新手提问
- 及时回应 PR 和 Issue

## 获得帮助

如果你有任何问题：

1. 查看 [文档](https://getaix.github.io/chronflow)
2. 搜索现有的 [Issues](https://github.com/getaix/chronflow/issues)
3. 创建新的 Issue 提问

## 致谢

感谢所有为 chronflow 做出贡献的开发者！你们的贡献让这个项目变得更好。

---

再次感谢你的贡献！🎉
