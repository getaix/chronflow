"""调度器守护进程控制模块。

本模块提供了将 Chronflow 调度器转为守护进程运行的能力,支持:
- 启动守护进程(使用 Unix fork)
- 停止守护进程(优雅终止或强制杀死)
- 重启守护进程(先停止再启动)
- 清理僵尸进程
- 通过 PID 文件或进程名管理进程生命周期

守护进程模式仅支持类 Unix 系统(Linux、macOS 等),不支持 Windows。

典型使用场景:
    ```python
    from chronflow import Scheduler

    scheduler = Scheduler()

    # 启动守护进程
    pid = await scheduler.start(daemon=True)
    print(f"守护进程已启动,PID: {pid}")

    # 停止守护进程
    await scheduler.stop(daemon=True)
    ```

设计说明:
- 使用 os.fork() 创建子进程,父进程立即返回
- 子进程调用 os.setsid() 独立会话,避免继承控制终端
- PID 文件用于追踪守护进程状态
- 支持 SIGTERM 优雅终止,超时后使用 SIGKILL 强制终止
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from chronflow.scheduler import Scheduler


class SchedulerDaemon:
    """调度器守护进程控制器。

    负责将调度器实例转换为后台守护进程运行,并提供完整的进程生命周期管理。

    属性:
        _scheduler: 关联的调度器实例
        _log: 日志适配器(复用调度器的日志配置)
        _pid_file: PID 文件路径,用于记录守护进程 PID
        _process_name: 进程标识名称,用于通过进程名查找 PID

    线程安全性:
        本类的所有公开方法都是异步的,内部使用 asyncio 进行协调,
        但 fork 和信号处理是系统级操作,需要特别注意多进程环境。
    """

    def __init__(self, scheduler: "Scheduler") -> None:
        """初始化守护进程控制器。

        参数:
            scheduler: 要管理的调度器实例

        注意:
            PID 文件路径和进程名称从调度器配置中读取。
        """
        self._scheduler = scheduler
        self._log = scheduler._log  # 复用调度器日志适配器
        self._pid_file = Path(scheduler.config.pid_file).expanduser()
        self._process_name = scheduler.config.process_name

    async def start(self) -> int:
        """启动守护进程并返回子进程 PID。

        工作流程:
        1. 检查操作系统是否支持守护模式(仅限类 Unix 系统)
        2. 检查是否已有守护进程在运行(通过 PID 文件)
        3. 如存在旧的僵尸进程,先清理
        4. 创建 PID 文件目录(如不存在)
        5. 使用 fork 创建子进程
        6. 父进程写入 PID 文件并返回子进程 PID
        7. 子进程调用 setsid 独立会话后启动调度器

        返回值:
            子进程的 PID(父进程视角)

        异常:
            RuntimeError: 在 Windows 系统上调用,或已有守护进程在运行

        注意:
            - 父进程会立即返回,不阻塞
            - 子进程会持续运行直到收到终止信号或发生错误
            - PID 文件由父进程和子进程都会写入(确保一致性)
        """
        if os.name == "nt":  # pragma: no cover - Windows 不支持 fork
            raise RuntimeError("守护模式仅支持类 Unix 系统")

        existing_pid = self._read_pid()
        if existing_pid and self._is_process_alive(existing_pid):
            raise RuntimeError(f"守护进程已在运行 (pid={existing_pid})")

        if existing_pid and not self._is_process_alive(existing_pid):
            await self.cleanup_zombies(pid=existing_pid)

        self._pid_file.parent.mkdir(parents=True, exist_ok=True)

        pid = os.fork()
        if pid != 0:
            # 父进程分支: 不写入 PID 文件,由子进程写入避免竞态
            # 短暂等待确保子进程已写入 PID 文件
            import time

            time.sleep(0.05)  # 等待 50ms

            self._log.info(
                "守护进程启动",
                pid=pid,
                pid_file=str(self._pid_file),
                process_name=self._process_name,
            )
            return pid

        # 子进程分支: 独立会话,避免重新继承控制终端
        os.setsid()

        # 重定向标准输入/输出/错误到 /dev/null,避免输出到终端
        import sys
        sys.stdin = open(os.devnull, "r")
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")

        self._run_daemon_process()
        os._exit(0)  # pragma: no cover - 子进程退出点

    async def stop(
        self,
        *,
        pid: int | None = None,
        name: str | None = None,
        timeout: float | None = None,
    ) -> bool:
        """停止守护进程(优雅终止或强制杀死)。

        停止流程:
        1. 解析目标 PID(通过 pid 参数、name 参数或 PID 文件)
        2. 向所有目标进程发送 SIGTERM 信号(优雅终止请求)
        3. 轮询等待进程终止,直到超时
        4. 超时后仍存活的进程,发送 SIGKILL 强制杀死
        5. 回收子进程资源并清理 PID 文件

        参数:
            pid: 指定要停止的进程 PID,优先级最高
            name: 根据进程名检索匹配的 PID(使用 pgrep -f)
            timeout: 等待优雅终止的超时时间(秒),默认 10 秒

        返回值:
            成功停止至少一个进程返回 True,未找到任何进程返回 False

        信号处理:
            - SIGTERM: 允许进程执行清理逻辑后退出
            - SIGKILL: 强制立即终止,无法被捕获或忽略

        注意:
            - 如果进程不存在(ProcessLookupError),会直接清理 PID 文件
            - 回收子进程(waitpid)避免产生僵尸进程
            - 支持同时停止多个匹配的进程(使用 name 参数时)
        """

        targets = self._resolve_pids(pid=pid, name=name)
        if not targets:
            return False

        deadline = time.monotonic() + (timeout or 10.0)
        # 第一阶段: 向所有目标发送 SIGTERM
        for target in targets:
            try:
                os.kill(target, signal.SIGTERM)
            except ProcessLookupError:
                self._cleanup_pid_file(target)
                continue

        # 第二阶段: 等待进程优雅退出
        for target in targets:
            while time.monotonic() < deadline and self._is_process_alive(target):
                await asyncio.sleep(0.2)

            # 第三阶段: 超时后强制杀死
            if self._is_process_alive(target):
                try:
                    os.kill(target, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            # 清理: 回收子进程并删除 PID 文件
            self._reap_child(target)
            self._cleanup_pid_file(target)

        return True

    async def restart(
        self,
        *,
        pid: int | None = None,
        name: str | None = None,
        timeout: float | None = None,
    ) -> int:
        """重启守护进程,返回新的 PID。

        重启流程:
        1. 停止现有守护进程(使用 stop 方法)
        2. 短暂延迟(0.1秒)确保旧进程完全释放资源
        3. 启动新的守护进程(使用 start 方法)

        参数:
            pid: 要重启的进程 PID(如不指定,从 PID 文件读取)
            name: 根据进程名匹配要重启的进程
            timeout: 停止旧进程的超时时间(秒)

        返回值:
            新启动的守护进程 PID

        异常:
            RuntimeError: 如果在 Windows 系统上调用,或启动失败

        注意:
            - 如果停止旧进程失败(如进程不存在),仍会尝试启动新进程
            - 确保资源(端口、文件锁等)已被旧进程完全释放
        """

        await self.stop(pid=pid, name=name, timeout=timeout)
        await asyncio.sleep(0.1)  # 等待旧进程完全释放资源(端口、文件锁等)
        return await self.start()

    async def cleanup_zombies(
        self,
        *,
        pid: int | None = None,
        name: str | None = None,
    ) -> bool:
        """检测并清理僵尸进程。

        僵尸进程(zombie process)是指子进程已终止但父进程未调用 waitpid 回收资源,
        导致进程表中仍保留进程条目(状态为 Z)。本方法用于清理这类"幽灵"进程。

        参数:
            pid: 要检查的进程 PID
            name: 根据进程名匹配要检查的进程

        返回值:
            成功清理至少一个僵尸进程返回 True,否则返回 False

        工作流程:
        1. 解析目标 PID
        2. 使用 `ps` 命令检查进程状态是否为 'Z'
        3. 如是僵尸进程,调用 waitpid 回收资源
        4. 清理对应的 PID 文件

        注意:
            - 僵尸进程不占用 CPU 和内存,但会占用进程表条目
            - 只有父进程才能回收其子进程的资源
            - 清理后进程将从进程表中彻底消失
        """

        cleaned = False
        for target_pid in self._resolve_pids(pid=pid, name=name):
            if self._is_zombie(target_pid):
                self._log.warning("检测到僵尸进程,尝试回收", pid=target_pid)
                self._reap_child(target_pid)
                self._cleanup_pid_file(target_pid)
                cleaned = True

        return cleaned

    def _run_daemon_process(self) -> None:
        """守护进程主体逻辑(在子进程中执行)。

        职责:
        1. 创建新的事件循环(与父进程隔离)
        2. 注册信号处理器(SIGTERM、SIGINT 触发优雅停止)
        3. 写入自身 PID 到文件
        4. 启动调度器并运行至完成
        5. 清理 PID 文件和事件循环资源

        信号处理:
            - SIGTERM/SIGINT: 触发调度器优雅停止(scheduler.stop)
            - 使用 call_soon_threadsafe 确保信号处理器与事件循环协调

        异常处理:
            - 所有未捕获的异常都会被记录日志但不会向上传播
            - 确保即使发生错误也能清理 PID 文件

        注意:
            - 本方法在子进程中调用,不应返回到父进程的代码路径
            - 事件循环是全新创建的,与父进程的事件循环完全独立
            - 退出时使用 os._exit(0) 而非 sys.exit(),避免清理父进程资源
        """

        # 创建独立的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 注册信号处理器: 收到终止信号时优雅停止调度器
        def _signal_handler(signum: int, _frame) -> None:
            """信号处理器,确保在事件循环可用时安全地停止调度器。"""

            def schedule_stop():
                try:
                    # 检查事件循环状态,避免在循环关闭时创建任务
                    if not loop.is_closed() and loop.is_running():
                        asyncio.create_task(self._scheduler.stop())
                    else:
                        # 事件循环不可用,直接设置停止标志
                        self._scheduler._shutdown_event.set()
                except RuntimeError as e:
                    # 如果仍然失败,记录错误并强制设置停止标志
                    try:
                        self._log.warning("信号处理器创建任务失败", error=str(e))
                    except Exception:
                        # 日志也可能失败,静默处理
                        pass
                    self._scheduler._shutdown_event.set()

            loop.call_soon_threadsafe(schedule_stop)

        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

        # 子进程记录自己的 PID (唯一写入点,避免与父进程竞态)
        self._write_pid(os.getpid())

        try:
            # 启动调度器(非守护模式,避免递归 fork)
            loop.run_until_complete(self._scheduler.start(daemon=False))
        except Exception as exc:  # pragma: no cover - 极端错误日志
            self._log.error("守护进程异常退出", error=str(exc), exc_info=True)
        finally:
            # 清理资源
            self._cleanup_pid_file(os.getpid())
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def _resolve_pids(self, *, pid: int | None, name: str | None) -> list[int]:
        """解析要操作的目标 PID 列表。

        参数优先级: pid > name > PID 文件

        返回值:
            匹配的 PID 列表(可能为空)
        """
        if pid:
            return [pid]
        if name:
            return self._find_pids_by_name(name)

        stored_pid = self._read_pid()
        return [stored_pid] if stored_pid else []

    def _read_pid(self) -> int | None:
        """从 PID 文件读取存储的 PID。

        返回值:
            存储的 PID,如文件不存在或内容无效则返回 None
        """
        if not self._pid_file.exists():
            return None

        try:
            content = self._pid_file.read_text().strip()
            return int(content) if content else None
        except (OSError, ValueError):
            return None

    def _write_pid(self, pid: int) -> None:
        """将 PID 写入文件。

        注意:
            - 如父目录不存在,会自动创建
            - 设置安全的文件权限 (0o644)
            - 写入失败会记录错误日志但不抛出异常

        安全性:
            - 目录权限设置为 0o755 (rwxr-xr-x)
            - 文件权限设置为 0o644 (rw-r--r--)
            - 防止其他用户修改 PID 文件
        """
        import stat

        try:
            # 创建目录并设置权限
            self._pid_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)

            # 写入 PID
            self._pid_file.write_text(str(pid))

            # 设置文件权限为 rw-r--r-- (644)
            self._pid_file.chmod(
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            )
        except OSError as exc:  # pragma: no cover
            self._log.error("写入 PID 文件失败", pid_file=str(self._pid_file), error=str(exc))

    def _cleanup_pid_file(self, pid: int) -> None:
        """清理 PID 文件(仅当文件中的 PID 匹配时)。

        参数:
            pid: 期望的 PID,如文件中记录的 PID 与此不符则不删除

        安全性:
            - 避免误删其他守护进程的 PID 文件
            - 删除失败不抛出异常(静默失败)
        """
        stored_pid = self._read_pid()
        if stored_pid and stored_pid != pid:
            return

        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - 忽略清理失败
            pass

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活。

        使用 os.kill(pid, 0) 探测,不发送真实信号:
        - 如果进程存在,返回 True
        - 如果进程不存在,抛出 ProcessLookupError,返回 False
        - 如果无权限检查,抛出 PermissionError,保守地返回 True

        返回值:
            进程存活返回 True,确认不存在返回 False
        """
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:  # pragma: no cover - 无权限仍认为存活
            return True

    def _reap_child(self, pid: int) -> None:
        """回收子进程资源,避免产生僵尸进程。

        使用 os.waitpid 的 WNOHANG 选项非阻塞地回收:
        - 如果子进程已终止,回收资源并返回
        - 如果子进程未终止,立即返回 0
        - 循环调用直到所有资源被回收

        异常处理:
            - ChildProcessError: 进程不是当前进程的子进程,忽略

        安全保护:
            - 最多重试 100 次,避免无限循环
        """
        max_attempts = 100
        try:
            for attempt in range(max_attempts):
                waited_pid, _ = os.waitpid(pid, os.WNOHANG)
                if waited_pid == 0:
                    # 子进程还未终止
                    break
                if waited_pid == pid:
                    # 成功回收子进程
                    break
            else:
                # 超过最大重试次数,记录警告
                self._log.warning(
                    "无法回收子进程资源",
                    pid=pid,
                    max_attempts=max_attempts,
                )
        except ChildProcessError:
            # 进程不是当前进程的子进程,或已被回收
            pass

    def _find_pids_by_name(self, name: str) -> list[int]:
        """根据进程名查找匹配的 PID。

        使用 `pgrep -fx <name>` 精确匹配命令行。

        参数:
            name: 要匹配的进程名或命令行片段

        返回值:
            匹配的 PID 列表(可能为空)

        注意:
            - 如果 pgrep 命令不存在或执行失败,返回空列表
            - -fx 选项会精确匹配完整的命令行
            - 添加了输入验证和超时保护

        安全性:
            - 验证输入长度,防止恶意输入
            - 使用 -x 精确匹配,避免误匹配其他进程
            - 添加超时限制,防止命令挂起
        """
        # 输入验证
        if not name or len(name) > 255:
            self._log.warning("进程名称无效", name=name)
            return []

        try:
            output = subprocess.check_output(
                ["pgrep", "-fx", name],  # -x 精确匹配
                stderr=subprocess.DEVNULL,
                timeout=5,  # 5秒超时
            )
        except subprocess.TimeoutExpired:
            self._log.warning("查找进程超时", name=name)
            return []
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

        return [int(line) for line in output.decode().splitlines() if line.strip()]

    def _is_zombie(self, pid: int) -> bool:
        """检查进程是否为僵尸状态。

        使用 `ps -p <pid> -o state=` 获取进程状态:
        - Z: 僵尸进程(已终止但未被回收)
        - 其他状态(R、S、D、T 等): 正常进程

        返回值:
            进程状态为 'Z' 返回 True,否则返回 False

        注意:
            - 如果进程不存在或 ps 命令失败,返回 False
        """
        try:
            output = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "state="],
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

        state = output.decode().strip()
        return bool(state) and state[0].upper() == "Z"
