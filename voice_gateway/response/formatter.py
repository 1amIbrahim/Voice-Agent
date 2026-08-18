"""Convert structured agent events into concise spoken responses."""

from enum import Enum
from typing import Optional

from voice_gateway.protocol import Event, EventType


class DetailLevel(str, Enum):
    BRIEF = "brief"
    NORMAL = "normal"
    DETAILED = "detailed"
    VERBOSE = "verbose"


class ResponseFormatter:
    def format(self, event: Event, detail: DetailLevel = DetailLevel.NORMAL) -> Optional[str]:
        if event.event is EventType.AGENT_STARTED:
            return None
        if event.event is EventType.AGENT_PROGRESS:
            return None
        if event.event is EventType.AGENT_COMPLETED:
            message = event.content.get("message", "The task is complete.")
            if detail in (DetailLevel.DETAILED, DetailLevel.VERBOSE):
                instruction = event.content.get("instruction")
                if instruction:
                    return f"{message}. Completed request: {instruction}."
            return str(message) + "."
        if event.event is EventType.AGENT_FAILED:
            reason = event.content.get("message", "The agent failed to complete the task")
            return f"{reason}."
        if event.event is EventType.AGENT_QUESTION:
            return str(event.content.get("message", "The agent has a question."))
        if event.event is EventType.AGENT_PERMISSION_REQUIRED:
            return str(event.content.get("message", "The agent needs your permission to continue."))
        if event.event is EventType.SYSTEM_WARNING:
            return str(event.content.get("message", "There is a warning."))
        if event.event is EventType.SYSTEM_ERROR:
            return str(event.content.get("message", "A system error occurred."))
        return None
