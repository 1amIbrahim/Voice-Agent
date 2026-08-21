"""Plan-mode Claude Code routing adapter."""

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional, Tuple

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
        base = {
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

        try:
            _log("starting Claude Code in plan mode")
            output = await self._run(command)
            message = self._message(output)
            _log("Claude Code completed")
        except asyncio.TimeoutError:
            _log("Claude Code timed out")
            yield Event(
                event=EventType.AGENT_FAILED,
                content={"message": "Claude Code did not finish before the configured timeout."},
                **base,
            )
            return
        except (OSError, RuntimeError, ValueError) as exc:
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
            },
            **base,
        )

    async def _run(self, command: Event) -> Dict[str, Any]:
        executable = self._resolve_executable()
        _log(f"launching Claude Code executable: {executable}")
        process = await self._process_factory(
            *self._command(self._prompt(command), executable),
            cwd=str(self.workspace),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            await self._stop_process(process)
            raise

        if process.returncode != 0:
            raise RuntimeError("Claude Code could not complete the command.")
        try:
            response = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Claude Code returned an invalid command response.") from exc
        if not isinstance(response, dict):
            raise RuntimeError("Claude Code returned an invalid command response.")
        if response.get("is_error"):
            raise RuntimeError("Claude Code could not complete the command.")
        return response

    async def _stop_process(self, process: Any) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.communicate(), timeout=5)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()

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
            "json",
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
        return result.strip()[:4000]
