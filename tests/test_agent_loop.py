import pytest

from voice_gateway.protocol import EventType, UserCommand, user_command
from voice_gateway.response import DetailLevel, ResponseFormatter
from voice_gateway.routing import FakeAgentPlatform
from voice_gateway.tts import PiperTTS


@pytest.mark.asyncio
async def test_fake_agent_emits_correlated_lifecycle_events():
    command = user_command(
        UserCommand(intent="delegate_task", instruction="Check the research folder"),
        session_id="session_123",
    )
    events = [event async for event in FakeAgentPlatform().dispatch(command)]

    assert [event.event for event in events] == [
        EventType.AGENT_STARTED,
        EventType.AGENT_PROGRESS,
        EventType.AGENT_COMPLETED,
    ]
    assert all(event.correlation_id == command.id for event in events)
    assert len({event.task_id for event in events}) == 1


def test_response_formatter_filters_progress_and_summarizes_completion():
    command = user_command(
        UserCommand(intent="delegate_task", instruction="Check the research folder"),
        session_id="session_123",
    )
    event = command.model_copy(
        update={
            "event": EventType.AGENT_COMPLETED,
            "content": {"message": "Task completed", "instruction": "Check the research folder"},
            "source": "fake-agent",
            "task_id": "task_123",
        }
    )
    formatter = ResponseFormatter()

    assert formatter.format(event, DetailLevel.BRIEF) == "Task completed."
    assert "Check the research folder" in formatter.format(event, DetailLevel.DETAILED)


def test_piper_requires_model_before_running():
    with pytest.raises(RuntimeError, match="model path"):
        PiperTTS().synthesize("Hello", "output.wav")
