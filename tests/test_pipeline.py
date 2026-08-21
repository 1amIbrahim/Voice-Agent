import pytest

from voice_gateway.pipeline import VoicePipeline
from voice_gateway.protocol import EventType, Event, Priority
from voice_gateway.response import DetailLevel
from voice_gateway.notifications.queue import NotificationQueue


@pytest.mark.asyncio
async def test_pipeline_connects_transcript_to_agent_response():
    result = await VoicePipeline().process_transcript("Tell Claude to check the research folder")

    assert result.command.event is EventType.USER_COMMAND
    assert result.command.content["target"] == "claude"
    assert result.agent_events[-1].event is EventType.AGENT_COMPLETED
    assert result.responses == ["Task completed."]


@pytest.mark.asyncio
async def test_pipeline_dispatches_explore_command():
    result = await VoicePipeline().process_transcript("Explore the directory.")

    assert result.command.event is EventType.USER_COMMAND
    assert result.agent_events[-1].event is EventType.AGENT_COMPLETED
    assert result.responses == ["Task completed."]


@pytest.mark.asyncio
async def test_pipeline_returns_clarification_without_dispatching():
    result = await VoicePipeline().process_transcript("Tell it to fix that")

    assert result.command.content["intent"] == "CLARIFICATION"
    assert result.agent_events == []
    assert result.responses == ["What should I apply that to?"]


@pytest.mark.asyncio
async def test_pipeline_preserves_constraints():
    result = await VoicePipeline().process_transcript(
        "Don't delete anything, just merge the duplicate notes"
    )

    assert "do_not_delete_information" in result.command.content["constraints"]


def test_notification_queue_prioritizes_high_events():
    queue = NotificationQueue()
    for priority in (Priority.LOW, Priority.HIGH, Priority.NORMAL):
        queue.put(Event(event=EventType.SYSTEM_NOTIFICATION, source="test", session_id="s", priority=priority))

    assert queue.get().priority is Priority.HIGH
    assert queue.get().priority is Priority.NORMAL
    assert queue.get().priority is Priority.LOW
