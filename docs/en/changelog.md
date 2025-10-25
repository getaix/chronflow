# Changelog

This document records all notable changes to symphra_scheduler.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and versioning adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2025-10-25

- Project renamed: chronflow -> symphra-scheduler; Python package: symphra_scheduler.
- Documentation, site, and repository links updated.

## [0.3.0] - 2025-10-24

### Added ✨

#### Task Discovery
- 🔍 Add `TaskDiscovery` class to automatically scan and register scheduled tasks
- 📁 Directory scanning supported — `discover_tasks_from_directory()`
- 📦 Package scanning supported — `discover_tasks_from_package()`
- 📝 Import from module list — `discover_tasks_from_modules()`
- 🎯 Wildcard file matching (e.g., `task.py`, `*_tasks.py`)
- ♻️ Recursive subdirectory scanning
- 🚫 Exclude specific file patterns
- ✅ Automatically register discovered tasks to the scheduler
- 🛡️ Fault tolerant — skip modules that fail to import

#### Scheduler Integration
- Add convenience `discover_tasks_from_directory()` method
- Add convenience `discover_tasks_from_package()` method
- Add convenience `discover_tasks_from_modules()` method

### Fixed 🐛

- 🔧 Fix second-level precision for Cron expressions
  - Add `second_at_beginning=True` in `croniter` calls
  - Ensure 6-field Cron expressions work (`second minute hour day month week`)
  - Fix `@daily()`, `@hourly()`, `@weekly()`, `@monthly()` decorators

### Improved 🔧

- 📚 Update MkDocs config to include Task Discovery docs
- 📝 Add detailed Task Discovery usage docs and examples
- 🎯 Improve project integration examples with short interval demo

### Examples

- Add `examples/task_discovery_example.py` — basic discovery example
- Add `examples/project_integration_example.py` — real project integration example

### Docs

- Add `docs/task_discovery.md` — complete discovery docs
- Update `README.md` to include discovery feature overview
- Add `TASK_DISCOVERY_SUMMARY.md` — implementation summary

### Tests

- Add `tests/test_discovery.py` — 13 test cases covering all discovery features
- ✅ All 301 tests passing

---

## [0.1.0] - 2025-10-22

### Added ✨

#### Pluggable Logging System
- Introduce `LoggerAdapter` interface
- Built-in support for structlog, loguru, and Python stdlib logging
- Fully customizable logging implementation
- Support disabling logs (`NoOpAdapter`)
- structlog becomes optional dependency

#### Enhanced Monitoring
- `list_tasks()` — get detailed list of all tasks
- `get_task_count()` — statistics of tasks by status
- `get_task_by_status()` — filter by status
- `get_task_by_tag()` — filter by tag
- `pause_task()` — pause a task
- `resume_task()` — resume a task
- Task list includes success rate and average execution time

#### New Convenience Decorators
- `@every()` — intuitive interval tasks (`@every(minutes=30)`)
- `@hourly()` — hourly execution (`@hourly(minute=30)`)
- `@daily()` — daily execution (`@daily(hour=9, minute=30)`)
- `@weekly()` — weekly execution (`@weekly(day=1, hour=10)`)
- `@monthly()` — monthly execution (`@monthly(day=1)`) 

#### Python Version Support
- Add official support for Python 3.13
- Continue support for Python 3.11 and 3.12

### Improved 🔧

- Dependencies: make structlog optional by default
- Type hints: full coverage for new features
- Docs: add detailed new feature docs and examples
- Logging: improve format, support structured logs

### Examples

- Add `examples/advanced_features.py` — advanced features demo
- Add `examples/custom_logger.py` — custom logger demo

### Technical Details

#### Logging Architecture

```
LoggerAdapter (abstract base class)
    ├── StructlogAdapter (default, optional)
    ├── LoguruAdapter (optional)
    ├── StdlibAdapter (built-in)
    └── NoOpAdapter (built-in)
```

#### New Decorator Mapping

| Decorator   | Equivalent Cron  | Description       |
|-------------|------------------|-------------------|
| `@hourly()` | `0 0 * * * *`    | Every hour at 00  |
| `@daily()`  | `0 0 0 * * *`    | Every day at 00:00|
| `@weekly()` | `0 0 0 * * 0`    | Every Sunday 00:00|
| `@monthly()`| `0 0 0 1 * *`    | 1st day 00:00     |

### Breaking Changes ⚠️

None. Fully backward compatible.

### Known Issues

None.

### Security

No security-related updates.

## [0.2.1] - 2025-10-24

### Fixed 🐛

#### Signal Handling
- Fix inability to respond to Ctrl+C in foreground mode (#BUG-001)
  - Register signal handlers in non-daemon mode
  - Support graceful stop for SIGINT (Ctrl+C) and SIGTERM
  - Use `loop.call_soon_threadsafe()` for thread safety
  - Files: `symphra_scheduler/scheduler.py:709-726`

#### Logging System
- Fix LogRecord `exc_info` field override error (#BUG-002)
  - Extract `exc_info` from kwargs in adapters
  - Avoid conflict with Python stdlib `logging.LogRecord`
  - Use `exception()` for exceptions instead of `error(..., exc_info=True)`
  - Files: `symphra_scheduler/logging.py`, `symphra_scheduler/scheduler.py`

#### Task Scheduling
- Fix duplicate task execution causing too many connections (#BUG-003)
  - Add duplicate task check in decorators
  - Prevent re-registration when modules reload
  - Avoid Redis "Too many connections" errors
  - File: `symphra_scheduler/decorators.py:167-170`

#### Daemon
- Fix writing to terminal when running in background (#BUG-004)
  - Redirect stdin/stdout/stderr to `/dev/null` in daemon subprocess
  - Prevent daemon logs from interfering with the start terminal
  - File: `symphra_scheduler/daemon.py:131-135`

### Improved 🔧

#### Test Coverage
- Increase coverage from 87% to 91% (#IMPROVE-001)
  - Add `tests/test_coverage_improvement.py`
  - Add `tests/test_decorators_advanced.py`
  - Optimize `.coveragerc` to exclude visualization code
  - Total 288+ test cases

#### Docs
- Add detailed Integration Guide (#IMPROVE-002)
  - Guidance on integrating Symphra Scheduler properly
  - FAQs and best practices
  - Complete examples

### Breaking Changes ⚠️

None. Fully backward compatible with 0.2.0.

### Security

- Improve thread safety in signal handling
- Enhance daemon security/permissions

### Upgrade Notes

Upgrading from 0.2.0 to 0.2.1:

1. If you encounter duplicate task execution:
   - Check for modules being imported multiple times
   - Ensure decorators are used at module level, not inside functions/methods
   - Refer to Integration Guide for best practices

2. If using Loguru or custom logging:
   - No changes required; `exc_info` compatibility is handled

3. If using daemon mode:
   - Logs no longer print to terminal; configure log files instead

---

## [0.2.0] - 2025-10-23

This release includes new features and improvements:
- Add `symphra_scheduler/daemon.py` to support running scheduler as a daemon
- Enhanced metrics collection and visualization example (`examples/metrics_visualization.py`)
- Improved decorator and config mapping; higher test coverage
- Python 3.13 supported in CI; strong type safety maintained
- Docs and examples updated

### Breaking Changes ⚠️
None. Backward compatible.

### Known Issues
None.

---

## [Unreleased]

### Planned Features

- [ ] Web admin UI
- [ ] Prometheus metrics export
- [ ] Task dependencies
- [ ] Dynamic add/remove tasks
- [ ] Distributed lock support
- [ ] PostgreSQL backend support

---

## Version Notes

### [0.1.0] — First Beta

This is the first public beta of symphra_scheduler, including core features:

**Core Features:**
- High-performance async scheduler
- Multiple queue backends (Memory/SQLite/Redis/RabbitMQ)
- Smart retry mechanism
- Second-level Cron expression support
- Decorator-based API
- Comprehensive type hints
- Pluggable logging system
- Rich monitoring capabilities

**Queue Backends:**
- MemoryBackend — in-memory, zero dependencies
- SQLiteBackend — local persistence
- RedisBackend — distributed queue
- RabbitMQBackend — high-reliability message queue

**Decorators:**
- `@scheduled` — generic scheduler
- `@cron` — Cron expressions
- `@interval` — fixed intervals
- `@once` — one-off tasks
- `@every` — intuitive intervals
- `@hourly` — hourly
- `@daily` — daily
- `@weekly` — weekly
- `@monthly` — monthly

**Monitoring:**
- Task list queries
- Status statistics
- Tag filters
- Task control (pause/resume)
- Detailed metrics

**Logging:**
- Structlog
- Loguru
- Python logging
- Custom adapters
- Disable logs

**Test Coverage:**
- 60+ unit tests
- High coverage
- Multiple practical examples

---

## Contributing

Found a bug or have a feature idea? Please [open an Issue](https://github.com/getaix/symphra-scheduler/issues)!

## License

MIT License — see [LICENSE](https://github.com/getaix/symphra-scheduler/blob/main/LICENSE)
