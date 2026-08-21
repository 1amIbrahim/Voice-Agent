import asyncio
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from voice_gateway.protocol import EventType, UserCommand, user_command
from voice_gateway.routing import ClaudeCodeAgentPlatform


class FakeProcess:
    def __init__(self, stdout=b"", returncode=0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    async def communicate(self):
        return self.stdout, b"untrusted diagnostic output"

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class HangingProcess(FakeProcess):
    def __init__(self) -> None:
        super().__init__()
        self.returncode = None
        self.release = asyncio.Event()

    async def communicate(self):
        await self.release.wait()
        return b"", b""

    def terminate(self):
        super().terminate()
        self.returncode = -15
        self.release.set()


def command():
    return user_command(
        UserCommand(
            intent="delegate_task",
            instruction="Review the authentication flow",
            target="claude",
            constraints=["only_requested_scope"],
        ),
        session_id="session_123",
    )


@pytest.mark.asyncio
async def test_claude_code_runs_in_plan_mode_with_raw_json_payload(tmp_path):
    calls = []

    async def create_process(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess(json.dumps({"result": "Proposed review steps", "is_error": False}).encode())

    platform = ClaudeCodeAgentPlatform(
        workspace=tmp_path,
        executable=sys.executable,
        process_factory=create_process,
    )
    user_event = command()
    events = [event async for event in platform.dispatch(user_event)]

    args, kwargs = calls[0]
    assert args[0] == sys.executable
    assert args[1] == "-p"
    assert args[args.index("--model") + 1] == "sonnet"
    assert "--output-format" in args
    assert args[args.index("--output-format") + 1] == "json"
    assert args[args.index("--permission-mode") + 1] == "plan"
    assert "--tools" not in args
    assert "--no-session-persistence" in args
    assert kwargs["cwd"] == str(tmp_path)
    assert json.loads(args[2]) == {
        "instruction": "Review the authentication flow",
        "target": "claude",
        "constraints": ["only_requested_scope"],
        "session_id": "session_123",
    }

    assert [event.event for event in events] == [
        EventType.AGENT_STARTED,
        EventType.AGENT_COMPLETED,
    ]
    assert all(event.correlation_id == user_event.id for event in events)
    assert events[0].content["instruction"] == "Review the authentication flow"
    assert events[1].content["message"] == "Proposed review steps"
    assert events[1].content["mode"] == "plan"
    assert events[0].task_id == events[1].task_id
    assert events[0].correlation_id == events[1].correlation_id


@pytest.mark.asyncio
async def test_claude_code_maps_nonzero_exit_to_safe_failure(tmp_path):
    async def create_process(*args, **kwargs):
        return FakeProcess(returncode=1)

    platform = ClaudeCodeAgentPlatform(
        workspace=tmp_path,
        executable=sys.executable,
        process_factory=create_process,
    )
    events = [event async for event in platform.dispatch(command())]

    assert [event.event for event in events] == [EventType.AGENT_STARTED, EventType.AGENT_FAILED]
    assert events[-1].content["message"] == "Claude Code could not complete the command."
    assert "untrusted" not in events[-1].content["message"]


@pytest.mark.asyncio
async def test_claude_code_maps_invalid_json_to_safe_failure(tmp_path):
    async def create_process(*args, **kwargs):
        return FakeProcess(b"not json")

    platform = ClaudeCodeAgentPlatform(
        workspace=tmp_path,
        executable=sys.executable,
        process_factory=create_process,
    )
    events = [event async for event in platform.dispatch(command())]

    assert events[-1].event is EventType.AGENT_FAILED
    assert events[-1].content["message"] == "Claude Code returned an invalid command response."


@pytest.mark.asyncio
async def test_claude_code_terminates_timed_out_process(tmp_path):
    process = HangingProcess()

    async def create_process(*args, **kwargs):
        return process

    platform = ClaudeCodeAgentPlatform(
        workspace=tmp_path,
        executable=sys.executable,
        timeout_seconds=0.001,
        process_factory=create_process,
    )
    events = [event async for event in platform.dispatch(command())]

    assert process.terminated is True
    assert events[-1].event is EventType.AGENT_FAILED
    assert events[-1].content["message"] == "Claude Code did not finish before the configured timeout."


def test_claude_code_resolves_windows_npm_shim_to_native_executable(tmp_path):
    platform = ClaudeCodeAgentPlatform(workspace=tmp_path)
    shim = tmp_path / "npm" / "claude.cmd"
    native_executable = (
        shim.parent
        / "node_modules"
        / "@anthropic-ai"
        / "claude-code"
        / "bin"
        / "claude.exe"
    )
    native_executable.parent.mkdir(parents=True)
    native_executable.touch()

    with patch("voice_gateway.routing.claude_code.os.name", "nt"), patch(
        "voice_gateway.routing.claude_code.shutil.which",
        return_value=str(shim),
    ) as which:
        assert platform._resolve_executable() == str(native_executable)

    which.assert_called_once_with("claude.cmd")


def test_claude_code_rejects_windows_npm_shim_without_native_executable(tmp_path):
    platform = ClaudeCodeAgentPlatform(workspace=tmp_path)
    shim = tmp_path / "npm" / "claude.cmd"

    with patch("voice_gateway.routing.claude_code.os.name", "nt"), patch(
        "voice_gateway.routing.claude_code.shutil.which",
        return_value=str(shim),
    ):
        with pytest.raises(RuntimeError, match="native executable was not found"):
            platform._resolve_executable()


def test_claude_code_preserves_explicit_executable_path(tmp_path):
    executable = tmp_path / "claude.exe"
    executable.touch()
    platform = ClaudeCodeAgentPlatform(workspace=tmp_path, executable=str(executable))

    assert platform._resolve_executable() == str(executable)


def test_claude_code_reports_missing_executable(tmp_path):
    platform = ClaudeCodeAgentPlatform(workspace=tmp_path)

    with patch("voice_gateway.routing.claude_code.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="executable was not found"):
            platform._resolve_executable()


def test_claude_code_requires_real_workspace(tmp_path):
    with pytest.raises(ValueError, match="workspace does not exist"):
        ClaudeCodeAgentPlatform(workspace=tmp_path / "missing")


def test_claude_code_requires_positive_timeout(tmp_path):
    with pytest.raises(ValueError, match="timeout"):
        ClaudeCodeAgentPlatform(workspace=tmp_path, timeout_seconds=0)


def test_claude_code_requires_model(tmp_path):
    with pytest.raises(ValueError, match="model"):
        ClaudeCodeAgentPlatform(workspace=tmp_path, model="")


@pytest.mark.asyncio
async def test_claude_code_rejects_non_command_event(tmp_path):
    platform = ClaudeCodeAgentPlatform(workspace=tmp_path)
    event = command().model_copy(update={"event": EventType.USER_CONFIRMATION})

    with pytest.raises(ValueError, match="user.command"):
        events = platform.dispatch(event)
        await events.__anext__()
