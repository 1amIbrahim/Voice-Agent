"""Plan-mode Claude Code routing adapter."""

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, AsyncGenerator, AsyncIterator, Awaitable, Callable, Dict, Optional, Tuple

from voice_gateway.protocol import Event, EventType


ProcessFactory = Callable[..., Awaitable[Any]]


def _log(message: str) -> None:
    formatted = f"[voice-gateway] {message}"
    for stream in (sys.stderr, sys.stdout):
        try:
            print(formatted, file=stream, flush=True)
            return
        except (OSError, ValueError):
            continue


class ClaudeCodeAgentPlatform:
    """Run Claude Code with an explicit plan-mode permission boundary."""

    def __init__(
        self,
        workspace: Path,
        executable: str = "claude",
        model: str = "sonnet",
        timeout_seconds: float = 120.0,
        process_factory: Optional[ProcessFactory] = None,
    ) -> None:
        self.workspace = Path(workspace)
        if not self.workspace.is_dir():
            raise ValueError(f"Claude Code workspace does not exist: {self.workspace}")
        if not executable:
            raise ValueError("Claude Code executable must not be empty")
        if not model:
            raise ValueError("Claude Code model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("Claude Code timeout must be greater than zero")
        self.executable = executable
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._process_factory = process_factory or asyncio.create_subprocess_exec

    async def dispatch(self, command: Event) -> AsyncIterator[Event]:
        if command.event is not EventType.USER_COMMAND:
            raise ValueError("Claude Code accepts only user.command events")

        task_id = f"task_{command.id.removeprefix('evt_')}"
        base: Dict[str, Any] = {
            "source": "claude-code",
            "session_id": command.session_id,
            "correlation_id": command.id,
            "task_id": task_id,
        }
        yield Event(
            event=EventType.AGENT_STARTED,
            content={
                "agent": "claude-code",
                "mode": "plan",
                "instruction": command.content.get("instruction"),
                "acknowledgement": command.content.get("acknowledgement"),
            },
            **base,
        )

        started_at = time.perf_counter()
        final: Optional[Dict[str, Any]] = None
        stream: AsyncGenerator[Dict[str, Any], None] = self._stream(command)
        try:
            _log("starting Claude Code in plan mode")
            while True:
                remaining = self.timeout_seconds - (time.perf_counter() - started_at)
                if remaining <= 0:
                    raise asyncio.TimeoutError
                try:
                    record = await asyncio.wait_for(stream.__anext__(), timeout=remaining)
                except StopAsyncIteration:
                    break
                if record.get("type") == "result":
                    final = record
                    continue
                progress = self._progress(record, time.perf_counter() - started_at)
                if progress is not None:
                    yield Event(event=EventType.AGENT_PROGRESS, content=progress, **base)

            if final is None:
                raise RuntimeError("Claude Code returned an invalid command response.")
            if final.get("is_error") or final.get("subtype") != "success":
                raise RuntimeError("Claude Code could not complete the command.")
            message = self._message(final)
            _log(f"Claude Code result:\n{message}")
            _log(self._completion_status(final))
        except asyncio.TimeoutError:
            await stream.aclose()
            _log("Claude Code timed out")
            yield Event(
                event=EventType.AGENT_FAILED,
                content={"message": "Claude Code did not finish before the configured timeout."},
                **base,
            )
            return
        except (OSError, RuntimeError, ValueError) as exc:
            await stream.aclose()
            _log(f"Claude Code failed: {exc}")
            yield Event(
                event=EventType.AGENT_FAILED,
                content={"message": str(exc)},
                **base,
            )
            return

        yield Event(
            event=EventType.AGENT_COMPLETED,
            content={
                "message": message,
                "instruction": command.content.get("instruction"),
                "mode": "plan",
                **self._result_metadata(final),
            },
            **base,
        )

    async def _stream(self, command: Event) -> AsyncGenerator[Dict[str, Any], None]:
        executable = self._resolve_executable()
        _log(f"launching Claude Code executable: {executable}")
        process = await self._process_factory(
            *self._command(self._prompt(command), executable),
            cwd=str(self.workspace),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Claude Code process streams were not created.")
        stderr_task = asyncio.create_task(process.stderr.read())
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                try:
                    record = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    _log("ignored malformed Claude Code stream record")
                    continue
                if isinstance(record, dict):
                    yield record
            await process.wait()
            if process.returncode != 0:
                raise RuntimeError("Claude Code could not complete the command.")
        finally:
            if process.returncode is None:
                await self._stop_process(process)
            await stderr_task

    @staticmethod
    def _progress(record: Dict[str, Any], elapsed_seconds: float) -> Optional[Dict[str, Any]]:
        record_type = record.get("type")
        if record_type == "system" and record.get("subtype") == "init":
            content: Dict[str, Any] = {
                "message": "Claude Code initialized",
                "elapsed_seconds": elapsed_seconds,
            }
            model = record.get("model")
            if isinstance(model, str):
                content["model"] = model
            return content
        if record_type != "assistant":
            return None

        message = record.get("message")
        if not isinstance(message, dict):
            return None
        blocks = message.get("content")
        if not isinstance(blocks, list):
            return None
        tool_names = [
            str(block["name"])
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "tool_use"
            and isinstance(block.get("name"), str)
        ]
        text_present = any(
            isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
            and block.get("text", "").strip()
            for block in blocks
        )
        if tool_names:
            status = f"Claude Code is using {', '.join(tool_names)}"
        elif text_present:
            status = "Claude Code produced an update"
        else:
            return None

        content = {"message": status, "elapsed_seconds": elapsed_seconds}
        usage = message.get("usage")
        if isinstance(usage, dict):
            content["usage"] = {
                key: value
                for key, value in usage.items()
                if key in {
                    "input_tokens",
                    "output_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                }
                and isinstance(value, int)
            }
        return content

    @staticmethod
    def _completion_status(response: Dict[str, Any]) -> str:
        parts = ["Claude Code completed"]
        duration_ms = response.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            parts.append(f"in {duration_ms / 1000:.1f}s")
        usage = response.get("usage")
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                parts.append(f"using {input_tokens} input and {output_tokens} output tokens")
        return " ".join(parts)

    @staticmethod
    def _result_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        for key in (
            "duration_ms",
            "duration_api_ms",
            "ttft_ms",
            "num_turns",
            "total_cost_usd",
        ):
            value = response.get(key)
            if isinstance(value, (int, float)):
                metadata[key] = value
        usage = response.get("usage")
        if isinstance(usage, dict):
            metadata["usage"] = usage
        model_usage = response.get("modelUsage")
        if isinstance(model_usage, dict):
            metadata["model_usage"] = model_usage
        return metadata

    async def _stop_process(self, process: Any) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

    def _resolve_executable(self) -> str:
        candidate = Path(self.executable)
        if candidate.is_file():
            return str(candidate)
        if candidate.parent != Path("."):
            raise RuntimeError(f"Claude Code executable was not found: {candidate}")

        lookup_name = self.executable
        if os.name == "nt" and not candidate.suffix:
            lookup_name = f"{self.executable}.cmd"
        resolved = shutil.which(lookup_name)
        if not resolved:
            raise RuntimeError(
                "Claude Code executable was not found. Install Claude Code or pass an explicit executable path."
            )
        if os.name == "nt" and Path(resolved).suffix.lower() == ".cmd":
            native_executable = (
                Path(resolved).parent
                / "node_modules"
                / "@anthropic-ai"
                / "claude-code"
                / "bin"
                / "claude.exe"
            )
            if native_executable.is_file():
                return str(native_executable)
            raise RuntimeError(
                "Claude Code's native executable was not found next to its npm command shim. "
                "Reinstall Claude Code or pass an explicit executable path."
            )
        return resolved

    def _command(self, prompt: str, executable: Optional[str] = None) -> Tuple[str, ...]:
        return (
            executable or self.executable,
            "-p",
            prompt,
            "--model",
            self.model,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "plan",
            "--no-session-persistence",
        )

    @staticmethod
    def _prompt(command: Event) -> str:
        payload = {
            "instruction": command.content.get("instruction"),
            "target": command.content.get("target"),
            "constraints": command.content.get("constraints", []),
            "session_id": command.session_id,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _message(response: Dict[str, Any]) -> str:
        result = response.get("result")
        if not isinstance(result, str) or not result.strip():
            return "Claude Code completed the command."
        return result.strip()
