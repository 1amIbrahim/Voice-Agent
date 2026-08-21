"""Deterministic fake agent platform for integration experiments."""

from typing import AsyncIterator, Dict, Optional

from voice_gateway.protocol import Event, EventType


class FakeAgentPlatform:
    def __init__(self, agent_name: str = "fake-agent") -> None:
        if not agent_name:
            raise ValueError("agent_name must not be empty")
        self.agent_name = agent_name

    async def dispatch(self, command: Event) -> AsyncIterator[Event]:
        if command.event is not EventType.USER_COMMAND:
            raise ValueError("fake agent accepts only user.command events")

        task_id = f"task_{command.id.removeprefix('evt_')}"
        base = {
            "source": self.agent_name,
            "session_id": command.session_id,
            "correlation_id": command.id,
            "task_id": task_id,
        }
        yield Event(
            event=EventType.AGENT_STARTED,
            content={
                "agent": self.agent_name,
                "instruction": command.content.get("instruction"),
                "acknowledgement": command.content.get("acknowledgement"),
            },
            **base,
        )
        yield Event(
            event=EventType.AGENT_PROGRESS,
            content={"message": "Working on the request"},
            **base,
        )
        yield Event(
            event=EventType.AGENT_COMPLETED,
            content={
                "message": "Task completed",
                "instruction": command.content.get("instruction"),
            },
            **base,
        )
