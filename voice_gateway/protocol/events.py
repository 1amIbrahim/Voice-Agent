"""Typed, correlated events exchanged by the voice gateway."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    USER_COMMAND = "user.command"
    USER_QUERY = "user.query"
    USER_CONFIRMATION = "user.confirmation"
    USER_REJECTION = "user.rejection"
    USER_CANCELLATION = "user.cancellation"
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progress"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_QUESTION = "agent.question"
    AGENT_PERMISSION_REQUIRED = "agent.permission_required"
    SYSTEM_NOTIFICATION = "system.notification"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_ERROR = "system.error"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    event: EventType
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    session_id: str
    correlation_id: Optional[str] = None
    task_id: Optional[str] = None
    priority: Priority = Priority.NORMAL
    content: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version", "id", "source", "session_id")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event identifiers cannot be empty")
        return value

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value.astimezone(timezone.utc)


class UserCommand(BaseModel):
    intent: str
    instruction: str
    target: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False


def user_command(
    command: UserCommand,
    session_id: str,
    source: str = "voice",
    priority: Priority = Priority.NORMAL,
) -> Event:
    return Event(
        event=EventType.USER_COMMAND,
        source=source,
        session_id=session_id,
        correlation_id=None,
        content=command.model_dump(exclude_none=True),
        priority=priority,
    )
