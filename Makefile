.PHONY: help install dev-install test coverage lint format type-check clean build setup

help:
	@echo "fscheduler - 开发命令"
	@echo ""
	@echo "setup          - 初始化开发环境(使用 uv)"
	@echo "install        - 安装基础依赖"
	@echo "dev-install    - 安装开发依赖"
	@echo "test           - 运行测试"
	@echo "coverage       - 运行测试并生成覆盖率报告"
	@echo "lint           - 运行代码检查(ruff)"
	@echo "format         - 格式化代码(black + ruff)"
	@echo "type-check     - 运行类型检查(mypy)"
	@echo "clean          - 清理构建文件"
	@echo "build          - 构建发布包"

setup:
	@echo "使用 uv 初始化开发环境..."
	uv venv
	@echo "安装开发依赖..."
	uv pip install -e ".[dev]"
	@echo ""
	@echo "✓ 开发环境已就绪!"
	@echo "激活虚拟环境: source .venv/bin/activate"

install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[dev]"

test:
	pytest tests/ -v

coverage:
	pytest tests/ -v --cov=fscheduler --cov-report=html --cov-report=term
	@echo "覆盖率报告已生成到 htmlcov/index.html"

lint:
	ruff check fscheduler/ tests/

format:
	ruff check --fix fscheduler/ tests/
	black fscheduler/ tests/

type-check:
	mypy fscheduler/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.db" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*
