import asyncio
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from voice_gateway.protocol import EventType, UserCommand, user_command
from voice_gateway.routing import ClaudeCodeAgentPlatform


class FakeReader:
    def __init__(self, data=b"") -> None:
        self.lines = iter(data.splitlines(keepends=True))

    async def readline(self):
        return next(self.lines, b"")

    async def read(self):
        return b"untrusted diagnostic output"


class FakeProcess:
    def __init__(self, stdout=b"", returncode=0) -> None:
        self.stdout = FakeReader(stdout)
        self.stderr = FakeReader()
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    async def wait(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


class HangingReader(FakeReader):
    def __init__(self) -> None:
        self.release = asyncio.Event()

    async def readline(self):
        await self.release.wait()
        return b""


class HangingProcess(FakeProcess):
    def __init__(self) -> None:
        super().__init__()
        self.stdout = HangingReader()
        self.returncode = None

    async def wait(self):
        if self.returncode is None:
            await self.stdout.release.wait()
        return self.returncode

    def terminate(self):
        super().terminate()
        self.stdout.release.set()


def stream(*records):
    return b"".join(json.dumps(record).encode() + b"\n" for record in records)


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
async def test_claude_code_streams_progress_and_preserves_full_result(tmp_path):
    calls = []
    result = "x" * 5000
    output = stream(
        {"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "secret reasoning"},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "secret.py"}},
                ],
                "usage": {"input_tokens": 10, "output_tokens": 4},
            },
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": result,
            "duration_ms": 1200,
            "duration_api_ms": 900,
            "ttft_ms": 300,
            "num_turns": 2,
            "total_cost_usd": 0.01,
            "usage": {"input_tokens": 20, "output_tokens": 8},
            "modelUsage": {"claude-sonnet-5": {"inputTokens": 20}},
        },
    )

    async def create_process(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess(output)

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
    assert args[args.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in args
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
        EventType.AGENT_PROGRESS,
        EventType.AGENT_PROGRESS,
        EventType.AGENT_COMPLETED,
    ]
    assert all(event.correlation_id == user_event.id for event in events)
    assert events[1].content["message"] == "Claude Code initialized"
    assert events[2].content["message"] == "Claude Code is using Read"
    assert "secret reasoning" not in str(events)
    assert "secret.py" not in str(events)
    assert events[2].content["usage"]["output_tokens"] == 4
    assert events[-1].content["message"] == result
    assert events[-1].content["duration_ms"] == 1200
    assert events[-1].content["usage"]["output_tokens"] == 8
    assert events[-1].content["model_usage"]["claude-sonnet-5"]["inputTokens"] == 20
    assert events[0].task_id == events[-1].task_id


def test_claude_code_completion_status_includes_time_and_tokens():
    status = ClaudeCodeAgentPlatform._completion_status(
        {
            "duration_ms": 12500,
            "usage": {"input_tokens": 100, "output_tokens": 25},
        }
    )

    assert status == "Claude Code completed in 12.5s using 100 input and 25 output tokens"


@pytest.mark.asyncio
async def test_claude_code_ignores_malformed_intermediate_line(tmp_path):
    output = b"not json\n" + stream(
        {"type": "result", "subtype": "success", "is_error": False, "result": "Done"}
    )

    async def create_process(*args, **kwargs):
        return FakeProcess(output)

    events = [
        event
        async for event in ClaudeCodeAgentPlatform(
            workspace=tmp_path,
            executable=sys.executable,
            process_factory=create_process,
        ).dispatch(command())
    ]

    assert events[-1].event is EventType.AGENT_COMPLETED
    assert events[-1].content["message"] == "Done"


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
async def test_claude_code_maps_missing_final_result_to_safe_failure(tmp_path):
    async def create_process(*args, **kwargs):
        return FakeProcess(b"not json\n")

    platform = ClaudeCodeAgentPlatform(
        workspace=tmp_path,
        executable=sys.executable,
        process_factory=create_process,
    )
    events = [event async for event in platform.dispatch(command())]

    assert events[-1].event is EventType.AGENT_FAILED
    assert events[-1].content["message"] == "Claude Code returned an invalid command response."


@pytest.mark.asyncio
async def test_claude_code_maps_error_result_to_safe_failure(tmp_path):
    output = stream({"type": "result", "subtype": "error", "is_error": True})

    async def create_process(*args, **kwargs):
        return FakeProcess(output)

    events = [
        event
        async for event in ClaudeCodeAgentPlatform(
            workspace=tmp_path,
            executable=sys.executable,
            process_factory=create_process,
        ).dispatch(command())
    ]

    assert events[-1].event is EventType.AGENT_FAILED
    assert events[-1].content["message"] == "Claude Code could not complete the command."


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
