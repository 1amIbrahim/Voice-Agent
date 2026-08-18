import pytest

from voice_gateway.context import SessionContext
from voice_gateway.pipeline import VoicePipeline
from voice_gateway.protocol import EventType


@pytest.mark.asyncio
async def test_context_resolves_follow_up_reference():
    pipeline = VoicePipeline(session_context=SessionContext())

    first = await pipeline.process_transcript("Tell Claude to check the research folder")
    follow_up = await pipeline.process_transcript("Tell it to fix that")

    assert first.command.content["target"] == "claude"
    assert follow_up.command.event is EventType.USER_COMMAND
    assert follow_up.command.content["target"] == "claude"
    assert follow_up.agent_events[-1].event is EventType.AGENT_COMPLETED


@pytest.mark.asyncio
async def test_sensitive_command_requires_confirmation_before_dispatch():
    pipeline = VoicePipeline()

    result = await pipeline.process_transcript("Tell Claude to delete the research folder")

    assert result.command.content["requires_confirmation"] is True
    assert result.agent_events == []
    assert "confirmation" in result.responses[0].lower()


@pytest.mark.asyncio
async def test_confirmation_dispatches_the_correlated_pending_command():
    pipeline = VoicePipeline()
    pending = await pipeline.process_transcript("Tell Claude to delete the research folder")

    approved = await pipeline.process_transcript("Yes")

    assert approved.command.event is EventType.USER_CONFIRMATION
    assert approved.command.correlation_id == pending.command.id
    assert approved.agent_events[-1].event is EventType.AGENT_COMPLETED


@pytest.mark.asyncio
async def test_rejection_clears_pending_command_without_dispatching():
    pipeline = VoicePipeline()
    pending = await pipeline.process_transcript("Tell Claude to delete the research folder")

    rejected = await pipeline.process_transcript("No")

    assert rejected.command.event is EventType.USER_REJECTION
    assert rejected.command.correlation_id == pending.command.id
    assert rejected.agent_events == []
    assert rejected.responses == ["The pending action was cancelled."]


@pytest.mark.asyncio
async def test_confirmation_without_pending_command_requests_clarification():
    result = await VoicePipeline().process_transcript("Yes")

    assert result.command.content["intent"] == "CLARIFICATION"
    assert result.responses == ["What action should I approve?"]
