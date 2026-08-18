from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from voice_gateway.protocol import Event, EventType, Priority, UserCommand, user_command


def test_user_command_event_has_required_correlations():
    event = user_command(
        UserCommand(
            intent="delegate_task",
            instruction="Review the research folder",
            target="claude",
            constraints=["do_not_delete_original_files"],
        ),
        session_id="session_123",
    )

    assert event.event is EventType.USER_COMMAND
    assert event.id.startswith("evt_")
    assert event.timestamp.tzinfo is not None
    assert event.content["target"] == "claude"


def test_event_normalizes_timestamp_to_utc():
    event = Event(
        event=EventType.AGENT_STARTED,
        source="agent",
        session_id="session_123",
        timestamp=datetime(2026, 8, 17, 17, 0, tzinfo=timezone.utc),
        priority=Priority.LOW,
    )

    assert event.timestamp.utcoffset().total_seconds() == 0


def test_event_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        Event(event="agent.unknown", source="agent", session_id="session_123")


def test_event_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Event(
            event=EventType.AGENT_STARTED,
            source="agent",
            session_id="session_123",
            unexpected="value",
        )


def test_event_rejects_naive_timestamp():
    with pytest.raises(ValidationError, match="timezone"):
        Event(
            event=EventType.AGENT_STARTED,
            source="agent",
            session_id="session_123",
            timestamp=datetime(2026, 8, 17, 17, 0),
        )


def test_protocol_round_trip_preserves_payload():
    event = user_command(
        UserCommand(intent="query", instruction="What is running?"),
        session_id="session_123",
    )
    restored = Event.model_validate_json(event.model_dump_json())

    assert restored == event
