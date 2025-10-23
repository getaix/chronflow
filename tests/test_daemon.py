"""守护进程控制器测试。"""

import asyncio
import os
import signal
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from chronflow.daemon import SchedulerDaemon
from chronflow.scheduler import Scheduler


class TestSchedulerDaemon:
    """守护进程控制器测试类。"""

    @pytest.fixture
    def temp_pid_file(self, tmp_path):
        """创建临时 PID 文件路径。"""
        return tmp_path / "daemon" / "test.pid"

    @pytest.fixture
    def scheduler(self, temp_pid_file):
        """创建测试用调度器。"""
        from chronflow.config import SchedulerConfig

        config = SchedulerConfig(
            enable_logging=False,
            pid_file=temp_pid_file,
            process_name="test-chronflow",
        )
        return Scheduler(config=config, use_global_scheduler=False)

    @pytest.fixture
    def daemon_controller(self, scheduler):
        """创建守护进程控制器实例。"""
        return SchedulerDaemon(scheduler)

    def test_daemon_initialization(self, daemon_controller, temp_pid_file):
        """测试守护进程控制器初始化。"""
        assert daemon_controller._pid_file == temp_pid_file
        assert daemon_controller._process_name == "test-chronflow"

    @pytest.mark.asyncio
    async def test_start_on_windows_raises_error(self, daemon_controller, monkeypatch):
        """测试在 Windows 系统上启动守护进程抛出错误。"""
        monkeypatch.setattr("chronflow.daemon.os.name", "nt")

        with pytest.raises(RuntimeError, match="守护模式仅支持类 Unix 系统"):
            await daemon_controller.start()

    @pytest.mark.asyncio
    async def test_start_with_existing_process(self, daemon_controller, temp_pid_file):
        """测试已有守护进程在运行时启动失败。"""
        # 模拟已有 PID 文件
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("12345")

        # 模拟进程存活
        with patch.object(daemon_controller, "_is_process_alive", return_value=True):
            with pytest.raises(RuntimeError, match="守护进程已在运行"):
                await daemon_controller.start()

    @pytest.mark.asyncio
    async def test_start_with_zombie_process(self, daemon_controller, temp_pid_file):
        """测试启动时自动清理僵尸进程。"""
        # 模拟已有 PID 文件但进程已死
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("12345")

        with patch.object(daemon_controller, "_is_process_alive", return_value=False):
            with patch.object(daemon_controller, "_is_zombie", return_value=True):
                with patch.object(daemon_controller, "_reap_child"):
                    with patch("chronflow.daemon.os.fork", return_value=99999):
                        pid = await daemon_controller.start()
                        assert pid == 99999
                        # PID 文件由子进程写入,父进程不写入(修复后的行为)

    @pytest.mark.asyncio
    async def test_start_creates_pid_file(self, daemon_controller, temp_pid_file):
        """测试启动守护进程创建 PID 文件。"""
        with patch("chronflow.daemon.os.fork", return_value=54321):
            pid = await daemon_controller.start()

            assert pid == 54321
            # PID 文件由子进程写入,父进程中不会立即存在(修复后的行为)

    @pytest.mark.asyncio
    async def test_stop_without_processes(self, daemon_controller):
        """测试停止不存在的守护进程。"""
        result = await daemon_controller.stop()
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_with_pid(self, daemon_controller):
        """测试通过 PID 停止守护进程。"""
        mock_target = 11111

        # 模拟进程在第一次检查时存活,后续检查时已死亡
        alive_checks = [True, False, False]  # 确保有足够的返回值

        with patch("chronflow.daemon.os.kill") as mock_kill:
            with patch.object(
                daemon_controller, "_is_process_alive", side_effect=lambda _: alive_checks.pop(0)
            ):
                with patch.object(daemon_controller, "_reap_child"):
                    with patch.object(daemon_controller, "_cleanup_pid_file"):
                        result = await daemon_controller.stop(pid=mock_target)

                        assert result is True
                        mock_kill.assert_called_once_with(mock_target, signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_stop_with_timeout_and_force_kill(self, daemon_controller):
        """测试超时后强制杀死进程。"""
        mock_target = 22222

        with patch("chronflow.daemon.os.kill") as mock_kill:
            with patch.object(daemon_controller, "_is_process_alive", return_value=True):
                with patch.object(daemon_controller, "_reap_child"):
                    with patch.object(daemon_controller, "_cleanup_pid_file"):
                        result = await daemon_controller.stop(pid=mock_target, timeout=0.1)

                        assert result is True
                        # 应该先发送 SIGTERM,然后发送 SIGKILL
                        assert mock_kill.call_count == 2

    @pytest.mark.asyncio
    async def test_stop_handles_process_lookup_error(self, daemon_controller):
        """测试停止时处理进程不存在错误。"""
        mock_target = 33333

        with patch("chronflow.daemon.os.kill", side_effect=ProcessLookupError):
            with patch.object(daemon_controller, "_cleanup_pid_file") as mock_cleanup:
                result = await daemon_controller.stop(pid=mock_target)

                assert result is True
                mock_cleanup.assert_called()

    @pytest.mark.asyncio
    async def test_restart(self, daemon_controller):
        """测试重启守护进程。"""
        with patch.object(daemon_controller, "stop", return_value=True) as mock_stop:
            with patch.object(daemon_controller, "start", return_value=99999) as mock_start:
                pid = await daemon_controller.restart(pid=44444, timeout=5.0)

                assert pid == 99999
                mock_stop.assert_called_once_with(pid=44444, name=None, timeout=5.0)
                mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_zombies_detects_and_cleans(self, daemon_controller, temp_pid_file):
        """测试检测并清理僵尸进程。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("55555")

        with patch.object(daemon_controller, "_is_zombie", return_value=True):
            with patch.object(daemon_controller, "_reap_child") as mock_reap:
                cleaned = await daemon_controller.cleanup_zombies()

                assert cleaned is True
                mock_reap.assert_called_once_with(55555)
                assert not temp_pid_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_zombies_ignores_normal_processes(self, daemon_controller, temp_pid_file):
        """测试不清理正常进程。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("66666")

        with patch.object(daemon_controller, "_is_zombie", return_value=False):
            cleaned = await daemon_controller.cleanup_zombies()

            assert cleaned is False

    def test_read_pid_from_file(self, daemon_controller, temp_pid_file):
        """测试从文件读取 PID。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("77777")

        pid = daemon_controller._read_pid()
        assert pid == 77777

    def test_read_pid_file_not_exists(self, daemon_controller):
        """测试 PID 文件不存在时返回 None。"""
        pid = daemon_controller._read_pid()
        assert pid is None

    def test_read_pid_invalid_content(self, daemon_controller, temp_pid_file):
        """测试 PID 文件内容无效时返回 None。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("not-a-number")

        pid = daemon_controller._read_pid()
        assert pid is None

    def test_write_pid_creates_directory(self, daemon_controller, temp_pid_file):
        """测试写入 PID 时自动创建目录。"""
        daemon_controller._write_pid(88888)

        assert temp_pid_file.exists()
        assert temp_pid_file.read_text().strip() == "88888"

    def test_cleanup_pid_file_only_if_matches(self, daemon_controller, temp_pid_file):
        """测试仅在 PID 匹配时清理文件。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("99999")

        # 不匹配的 PID,不应删除
        daemon_controller._cleanup_pid_file(11111)
        assert temp_pid_file.exists()

        # 匹配的 PID,应删除
        daemon_controller._cleanup_pid_file(99999)
        assert not temp_pid_file.exists()

    def test_is_process_alive(self, daemon_controller):
        """测试检查进程是否存活。"""
        # 测试当前进程(应该存活)
        current_pid = os.getpid()
        assert daemon_controller._is_process_alive(current_pid) is True

        # 测试不存在的进程
        with patch("chronflow.daemon.os.kill", side_effect=ProcessLookupError):
            assert daemon_controller._is_process_alive(99999) is False

        # 测试权限不足的进程(保守认为存活)
        with patch("chronflow.daemon.os.kill", side_effect=PermissionError):
            assert daemon_controller._is_process_alive(1) is True

    def test_reap_child(self, daemon_controller):
        """测试回收子进程资源。"""
        with patch("chronflow.daemon.os.waitpid") as mock_waitpid:
            # 模拟子进程已被回收
            mock_waitpid.return_value = (0, 0)
            daemon_controller._reap_child(12345)

            mock_waitpid.assert_called_once_with(12345, os.WNOHANG)

    def test_reap_child_handles_error(self, daemon_controller):
        """测试回收子进程时处理错误。"""
        with patch("chronflow.daemon.os.waitpid", side_effect=ChildProcessError):
            # 应该不抛出异常
            daemon_controller._reap_child(12345)

    def test_find_pids_by_name(self, daemon_controller):
        """测试根据进程名查找 PID。"""
        mock_output = b"1111\n2222\n3333\n"

        with patch("chronflow.daemon.subprocess.check_output", return_value=mock_output):
            pids = daemon_controller._find_pids_by_name("test-process")

            assert pids == [1111, 2222, 3333]

    def test_find_pids_by_name_no_results(self, daemon_controller):
        """测试查找进程名无结果。"""
        import subprocess

        with patch(
            "chronflow.daemon.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "pgrep"),
        ):
            pids = daemon_controller._find_pids_by_name("nonexistent")

            assert pids == []

    def test_is_zombie(self, daemon_controller):
        """测试检查进程是否为僵尸状态。"""
        import subprocess

        # 模拟僵尸进程
        with patch("chronflow.daemon.subprocess.check_output", return_value=b"Z\n"):
            assert daemon_controller._is_zombie(12345) is True

        # 模拟正常进程
        with patch("chronflow.daemon.subprocess.check_output", return_value=b"S\n"):
            assert daemon_controller._is_zombie(12345) is False

        # 模拟进程不存在
        with patch(
            "chronflow.daemon.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "ps"),
        ):
            assert daemon_controller._is_zombie(99999) is False

    def test_resolve_pids_priority(self, daemon_controller, temp_pid_file):
        """测试 PID 解析优先级。"""
        temp_pid_file.parent.mkdir(parents=True, exist_ok=True)
        temp_pid_file.write_text("11111")

        # 优先级1: 显式传入 PID
        pids = daemon_controller._resolve_pids(pid=22222, name="test")
        assert pids == [22222]

        # 优先级2: 通过进程名查找
        with patch.object(daemon_controller, "_find_pids_by_name", return_value=[33333, 44444]):
            pids = daemon_controller._resolve_pids(pid=None, name="test")
            assert pids == [33333, 44444]

        # 优先级3: 从 PID 文件读取
        pids = daemon_controller._resolve_pids(pid=None, name=None)
        assert pids == [11111]

        # 无法解析时返回空列表
        temp_pid_file.unlink()
        pids = daemon_controller._resolve_pids(pid=None, name=None)
        assert pids == []
