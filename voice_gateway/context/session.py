"""Session-scoped context for voice interpretation and authorization."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from voice_gateway.protocol import Event


@dataclass
class PendingConfirmation:
    command: Event
    message: str


@dataclass
class SessionContext:
    active_agent: Optional[str] = None
    active_task: Optional[str] = None
    pending_confirmation: Optional[PendingConfirmation] = None
    recent_command: Optional[Event] = None

    def interpretation_context(self) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        if self.active_agent:
            context["active_agent"] = self.active_agent
        if self.active_task:
            context["active_task"] = self.active_task
        if self.recent_command:
            context["recent_instruction"] = self.recent_command.content.get("instruction")
        return context

    def remember_command(self, command: Event) -> None:
        self.recent_command = command
        target = command.content.get("target")
        if isinstance(target, str) and target:
            self.active_agent = target
        instruction = command.content.get("instruction")
        if isinstance(instruction, str) and instruction:
            self.active_task = instruction
