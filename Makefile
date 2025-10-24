.PHONY: help install dev-install test coverage lint format type-check clean build setup docs-install docs-serve docs-build docs-clean

help:
	@echo "chronflow - 开发命令"
	@echo ""
	@echo "开发环境:"
	@echo "  setup          - 初始化开发环境(使用 uv)"
	@echo "  install        - 安装基础依赖"
	@echo "  dev-install    - 安装开发依赖"
	@echo ""
	@echo "测试与质量:"
	@echo "  test           - 运行测试"
	@echo "  coverage       - 运行测试并生成覆盖率报告"
	@echo "  lint           - 运行代码检查(ruff)"
	@echo "  format         - 格式化代码(black + ruff)"
	@echo "  type-check     - 运行类型检查(mypy)"
	@echo ""
	@echo "文档:"
	@echo "  docs-install   - 安装文档依赖"
	@echo "  docs-serve     - 启动文档预览服务器(http://127.0.0.1:8000)"
	@echo "  docs-build     - 构建静态文档到 site/ 目录"
	@echo "  docs-clean     - 清理文档构建文件"
	@echo ""
	@echo "构建与发布:"
	@echo "  clean          - 清理构建文件"
	@echo "  build          - 构建发布包"
	@echo "  publish        - 发布到 PyPI"

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
	pytest tests/ -v --cov=chronflow --cov-report=html --cov-report=term
	@echo "覆盖率报告已生成到 htmlcov/index.html"

lint:
	ruff check chronflow/ tests/

format:
	ruff check --fix chronflow/ tests/
	black chronflow/ tests/

type-check:
	mypy chronflow/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf site/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.db" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

# 文档命令
docs-install:
	@echo "安装文档依赖..."
	uv pip install -e ".[docs]"
	@echo "✓ 文档依赖已安装"

docs-serve: docs-install
	@echo "启动文档预览服务器..."
	@echo "访问: http://127.0.0.1:8000"
	mkdocs serve

docs-build: docs-install
	@echo "构建静态文档..."
	mkdocs build
	@echo "✓ 文档已构建到 site/ 目录"

docs-clean:
	@echo "清理文档构建文件..."
	rm -rf site/
	@echo "✓ 文档构建文件已清理"
