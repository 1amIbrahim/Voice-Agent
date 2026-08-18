import pytest

from voice_gateway.understanding import (
    IntentResult,
    IntentType,
    OllamaUnderstanding,
    RuleBasedUnderstanding,
)


@pytest.fixture
def interpreter():
    return RuleBasedUnderstanding()


def test_command_extracts_agent_and_instruction(interpreter):
    result = interpreter.interpret("Tell Claude to check the research folder.")

    assert result.intent is IntentType.COMMAND
    assert result.target_agent == "claude"
    assert result.entities == {"agent": "claude"}
    assert result.instruction == "Tell Claude to check the research folder."


def test_meaning_preserves_negation_and_constraints(interpreter):
    result = interpreter.interpret("Don't delete anything, just merge the duplicate notes.")

    assert result.intent is IntentType.COMMAND
    assert "do_not_delete_information" in result.constraints


def test_ambiguous_reference_requests_clarification(interpreter):
    result = interpreter.interpret("Tell it to fix that.")

    assert result.requires_clarification is True
    assert result.clarification_question


def test_context_can_resolve_reference(interpreter):
    result = interpreter.interpret(
        "Tell it to fix that.",
        context={"active_agent": "claude", "active_task": "parser.py"},
    )

    assert result.requires_clarification is False


def test_control_intents(interpreter):
    assert interpreter.interpret("Stop").intent is IntentType.CANCELLATION
    assert interpreter.interpret("Yes, please").intent is IntentType.CONFIRMATION
    assert interpreter.interpret("No").intent is IntentType.REJECTION


def test_empty_transcript_is_rejected(interpreter):
    with pytest.raises(ValueError, match="transcript"):
        interpreter.interpret("  ")


def test_intent_result_serializes_to_schema():
    result = IntentResult(intent=IntentType.QUERY, confidence=0.9)

    assert result.model_dump()["intent"] == "QUERY"
    assert "requires_clarification" in result.model_json_schema()["properties"]


def test_ollama_adapter_uses_validated_response():
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '{"intent":"COMMAND","target_agent":"claude","instruction":"check it","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                }
            }

    result = OllamaUnderstanding(client=FakeClient()).interpret("Tell Claude to check it")

    assert result.intent is IntentType.COMMAND
    assert result.confidence == pytest.approx(0.91)
