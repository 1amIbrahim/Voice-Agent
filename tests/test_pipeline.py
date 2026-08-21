import pytest

from voice_gateway.pipeline import VoicePipeline
from voice_gateway.protocol import EventType, Event, Priority
from voice_gateway.response import DetailLevel, ResponseFormatter
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
    started = []
    result = await VoicePipeline().process_transcript(
        "Explore the directory.",
        on_agent_started=started.append,
    )

    assert result.command.event is EventType.USER_COMMAND
    assert started[0].event is EventType.AGENT_STARTED
    assert result.agent_events[-1].event is EventType.AGENT_COMPLETED
    assert result.responses == ["Task completed."]


@pytest.mark.asyncio
async def test_pipeline_exits_conversation_without_dispatching():
    result = await VoicePipeline().process_transcript("End conversation")

    assert result.command.content["intent"] == "END_CONVERSATION"
    assert result.agent_events == []
    assert result.responses == ["Conversation ended. Goodbye."]


@pytest.mark.asyncio
async def test_pipeline_returns_conversation_reply_without_dispatching():
    class Conversation:
        def respond(self, transcript, context):
            assert transcript == "How are you?"
            return "I am ready. What would you like to do?"

    result = await VoicePipeline(conversation_engine=Conversation()).process_transcript("How are you?")

    assert result.command.content["intent"] == "QUERY"
    assert result.agent_events == []
    assert result.responses == ["I am ready. What would you like to do?"]


@pytest.mark.asyncio
async def test_pipeline_uses_understanding_as_conversation_engine():
    class Assistant:
        def interpret(self, transcript, context):
            from voice_gateway.understanding import IntentResult, IntentType

            return IntentResult(
                intent=IntentType.CONVERSATION,
                instruction=transcript,
                confidence=0.9,
            )

        def respond(self, transcript, context):
            return "Ready, sir."

    assistant = Assistant()
    pipeline = VoicePipeline(understanding=assistant)

    result = await pipeline.process_transcript("Hello")

    assert pipeline.conversation_engine is assistant
    assert result.responses == ["Ready, sir."]


@pytest.mark.asyncio
async def test_pipeline_passes_model_acknowledgement_to_agent_started_event():
    from voice_gateway.understanding import IntentResult, IntentType

    class Assistant:
        def interpret(self, transcript, context):
            return IntentResult(
                intent=IntentType.COMMAND,
                instruction=transcript,
                acknowledgement="Certainly, sir. I'll inspect it now.",
                confidence=0.9,
            )

    started = []
    await VoicePipeline(understanding=Assistant()).process_transcript(
        "Explore the directory.",
        on_agent_started=started.append,
    )

    assert started[0].content["acknowledgement"] == (
        "Certainly, sir. I'll inspect it now."
    )


@pytest.mark.asyncio
async def test_pipeline_remembers_agent_outcome_for_later_conversation():
    class Assistant:
        def __init__(self):
            self.exchanges = []

        def interpret(self, transcript, context):
            from voice_gateway.understanding import RuleBasedUnderstanding

            return RuleBasedUnderstanding().interpret(transcript, context)

        def respond(self, transcript, context):
            return "Ready, sir."

        def remember_exchange(self, user_text, assistant_text):
            self.exchanges.append((user_text, assistant_text))

    assistant = Assistant()
    await VoicePipeline(understanding=assistant).process_transcript(
        "Explore the directory."
    )

    assert assistant.exchanges == [("Explore the directory.", "Task completed.")]


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


def test_acknowledgement_uses_model_generated_statement():
    event = Event(
        event=EventType.AGENT_STARTED,
        source="test",
        session_id="s",
        content={
            "instruction": "Explore the directory.",
            "acknowledgement": "Right away, sir. I'll inspect the directory.",
        },
    )

    assert ResponseFormatter().acknowledgement(event) == (
        "Right away, sir. I'll inspect the directory."
    )


def test_acknowledgement_falls_back_to_command_instruction():
    event = Event(
        event=EventType.AGENT_STARTED,
        source="test",
        session_id="s",
        content={"instruction": "Explore the directory."},
    )

    assert ResponseFormatter().acknowledgement(event) == "Explore the directory, sir."


def test_notification_queue_prioritizes_high_events():
    queue = NotificationQueue()
    for priority in (Priority.LOW, Priority.HIGH, Priority.NORMAL):
        queue.put(Event(event=EventType.SYSTEM_NOTIFICATION, source="test", session_id="s", priority=priority))

    assert queue.get().priority is Priority.HIGH
    assert queue.get().priority is Priority.NORMAL
    assert queue.get().priority is Priority.LOW
