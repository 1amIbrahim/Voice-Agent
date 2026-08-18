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


def test_ollama_adapter_uses_system_prompt_and_transcript():
    class FakeClient:
        def chat(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "system"
            assert "voice-to-agent interpreter" in kwargs["messages"][0]["content"]
            assert kwargs["messages"][1]["role"] == "user"
            assert "Tell Claude to check it" in kwargs["messages"][1]["content"]
            return {
                "message": {
                    "content": '{"intent":"COMMAND","target_agent":"claude","instruction":"check it","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                }
            }

    result = OllamaUnderstanding(client=FakeClient()).interpret("Tell Claude to check it")

    assert result.intent is IntentType.COMMAND
    assert result.confidence == pytest.approx(0.91)


def test_ollama_adapter_logs_raw_response(capsys):
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '{"intent":"COMMAND","target_agent":"claude","instruction":"check research","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                }
            }

    OllamaUnderstanding(client=FakeClient()).interpret("Tell Claude to check research")

    assert "understanding raw response" in capsys.readouterr().err


def test_ollama_adapter_accepts_fenced_json():
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '```json\n{"intent":"COMMAND","target_agent":"claude","instruction":"check research","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}\n```'
                }
            }

    result = OllamaUnderstanding(client=FakeClient()).interpret("Tell Claude to check research")

    assert result.instruction == "check research"


def test_ollama_system_prompt_requires_structured_non_executing_interpretation():
    prompt = OllamaUnderstanding.SYSTEM_PROMPT

    assert "voice-to-agent interpreter" in prompt
    assert "agent-facing instruction" in prompt
    assert "Preserve negation" in prompt
    assert "requires_clarification=true" in prompt
    assert "valid JSON" in prompt


def test_ollama_prompt_includes_context():
    prompt = OllamaUnderstanding._prompt(
        "Tell it to fix that.",
        {"active_agent": "claude", "active_task": "parser.py"},
    )

    assert "Tell it to fix that." in prompt
    assert "active_agent" in prompt
    assert "parser.py" in prompt
