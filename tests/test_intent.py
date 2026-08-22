import pytest

from voice_gateway.understanding import (
    GeminiAssistant,
    IntentResult,
    IntentType,
    OllamaAssistant,
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


def test_explore_is_a_command(interpreter):
    result = interpreter.interpret("Explore the directory.")

    assert result.intent is IntentType.COMMAND
    assert result.instruction == "Explore the directory."


def test_polite_read_request_is_a_command(interpreter):
    transcript = "Can you read the readme file only? Just get the readme file for me."

    result = interpreter.interpret(transcript)

    assert result.intent is IntentType.COMMAND
    assert result.instruction == transcript
    assert "only_requested_scope" in result.constraints


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
    assert interpreter.interpret("End conversation").intent is IntentType.END_CONVERSATION
    assert interpreter.interpret("Stand by").intent is IntentType.STANDBY
    assert interpreter.interpret("Standby.").intent is IntentType.STANDBY


def test_empty_transcript_is_rejected(interpreter):
    with pytest.raises(ValueError, match="transcript"):
        interpreter.interpret("  ")


def test_intent_result_serializes_to_schema():
    result = IntentResult(intent=IntentType.QUERY, confidence=0.9)

    assert result.model_dump()["intent"] == "QUERY"
    properties = result.model_json_schema()["properties"]
    assert "requires_clarification" in properties
    assert "acknowledgement" in properties


def test_ollama_assistant_skips_model_for_standby():
    class FakeClient:
        def chat(self, **kwargs):
            raise AssertionError("model should not be called")

    result = OllamaAssistant(client=FakeClient()).interpret("Stand by")

    assert result.intent is IntentType.STANDBY


def test_gemini_assistant_skips_model_for_standby():
    class FakeClient:
        interactions = None

    result = GeminiAssistant(client=FakeClient()).interpret("Stand by")

    assert result.intent is IntentType.STANDBY


def test_ollama_assistant_uses_non_thinking_only_for_intent():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def chat(self, **kwargs):
            self.calls.append(kwargs)
            if "format" in kwargs:
                return {
                    "message": {
                        "content": '{"intent":"QUERY","target_agent":null,"instruction":"How are you?","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                    }
                }
            return {"message": {"content": "Fully operational, sir."}}

    client = FakeClient()
    assistant = OllamaAssistant(client=client)

    assistant.interpret("How are you?")
    reply = assistant.respond("How are you?")

    assert reply == "Fully operational, sir."
    assert client.calls[0]["messages"][0]["content"].startswith("/no_think")
    assert "format" in client.calls[0]
    assert not client.calls[1]["messages"][0]["content"].startswith("/no_think")
    assert "format" not in client.calls[1]
    assert "conversational voice of a local" in client.calls[1]["messages"][0]["content"]


def test_ollama_assistant_intent_prompt_includes_transcript_context_and_history():
    class FakeClient:
        def chat(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "system"
            assert kwargs["messages"][1]["role"] == "user"
            user_prompt = kwargs["messages"][1]["content"]
            assert "Tell Claude to check it" in user_prompt
            assert "active_agent" in user_prompt
            assert "Earlier result" in user_prompt
            return {
                "message": {
                    "content": '{"intent":"COMMAND","target_agent":"claude","instruction":"check it","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                }
            }

    assistant = OllamaAssistant(client=FakeClient())
    assistant.remember_exchange("Earlier command", "Earlier result")
    result = assistant.interpret(
        "Tell Claude to check it",
        {"active_agent": "claude"},
    )

    assert result.intent is IntentType.COMMAND
    assert result.confidence == pytest.approx(0.91)


def test_ollama_assistant_rejects_false_control_intent_for_command():
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '{"intent":"REJECTION","target_agent":null,"instruction":null,"entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":1.0}'
                }
            }

    result = OllamaAssistant(client=FakeClient()).interpret("Explore the directory.")

    assert result.intent is IntentType.COMMAND
    assert result.instruction == "Explore the directory."


def test_ollama_assistant_rejects_non_command_for_explicit_polite_command():
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '{"intent":"CONVERSATION","target_agent":null,"instruction":"I cannot read files.","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.9}'
                }
            }

    transcript = "Can you read the readme file only? Just get the readme file for me."
    result = OllamaAssistant(client=FakeClient()).interpret(transcript)

    assert result.intent is IntentType.COMMAND
    assert result.instruction == transcript
    assert "only_requested_scope" in result.constraints


def test_ollama_assistant_handles_explicit_control_without_model_call():
    class FailingClient:
        def chat(self, **kwargs):
            raise AssertionError("explicit controls must not call the model")

    result = OllamaAssistant(client=FailingClient()).interpret("No")

    assert result.intent is IntentType.REJECTION


def test_ollama_assistant_logs_raw_response(capsys):
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '{"intent":"COMMAND","target_agent":"claude","instruction":"check research","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                }
            }

    OllamaAssistant(client=FakeClient()).interpret("Tell Claude to check research")

    assert "understanding raw response" in capsys.readouterr().err


def test_ollama_assistant_accepts_fenced_json():
    class FakeClient:
        def chat(self, **kwargs):
            return {
                "message": {
                    "content": '```json\n{"intent":"COMMAND","target_agent":"claude","instruction":"check research","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}\n```'
                }
            }

    result = OllamaAssistant(client=FakeClient()).interpret("Tell Claude to check research")

    assert result.instruction == "check research"


def test_ollama_assistant_bounds_natural_history_without_intent_json():
    assistant = OllamaAssistant(client=object(), max_history_messages=4)

    assistant.remember_exchange("first", "one")
    assistant.remember_exchange("second", "two")
    assistant.remember_exchange("third", "three")

    assert assistant.history == [
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "third"},
        {"role": "assistant", "content": "three"},
    ]
    assert all('"intent"' not in message["content"] for message in assistant.history)


def test_ollama_intent_prompt_requires_structured_non_executing_interpretation():
    prompt = OllamaAssistant.INTENT_SYSTEM_PROMPT

    assert prompt.startswith("/no_think")
    assert "agent-facing instruction" in prompt
    assert "Preserve the user's requested scope" in prompt
    assert "requires_clarification=true" in prompt
    assert "include an acknowledgement" in prompt
    assert "never claim" in prompt
    assert "Do not execute commands" in prompt


def test_gemini_assistant_uses_interactions_for_intent_and_conversation():
    class Interaction:
        def __init__(self, output_text):
            self.output_text = output_text

    class Interactions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if "schema" in kwargs["input"]:
                return Interaction(
                    '{"intent":"QUERY","target_agent":null,"instruction":"How are you?","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'
                )
            return Interaction("Fully operational, sir.")

    class FakeClient:
        def __init__(self):
            self.interactions = Interactions()

    client = FakeClient()
    assistant = GeminiAssistant(client=client)

    intent = assistant.interpret("How are you?")
    reply = assistant.respond("How are you?")

    assert intent.intent is IntentType.QUERY
    assert reply == "Fully operational, sir."
    assert client.interactions.calls[0]["model"] == "gemini-3.7-flash"
    assert "schema" in client.interactions.calls[0]["input"]
    assert "schema" not in client.interactions.calls[1]["input"]


def test_gemini_assistant_handles_explicit_control_without_api_call():
    class FailingInteractions:
        def create(self, **kwargs):
            raise AssertionError("explicit controls must not call Gemini")

    class FakeClient:
        interactions = FailingInteractions()

    result = GeminiAssistant(client=FakeClient()).interpret("End conversation")

    assert result.intent is IntentType.END_CONVERSATION


def test_gemini_assistant_rejects_false_control_for_command():
    class Interaction:
        output_text = '{"intent":"REJECTION","target_agent":null,"instruction":null,"entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":1.0}'

    class Interactions:
        def create(self, **kwargs):
            return Interaction()

    class FakeClient:
        interactions = Interactions()

    result = GeminiAssistant(client=FakeClient()).interpret("Explore the directory.")

    assert result.intent is IntentType.COMMAND
    assert result.instruction == "Explore the directory."


def test_gemini_assistant_bounds_shared_history():
    assistant = GeminiAssistant(client=object(), max_history_messages=2)

    assistant.remember_exchange("first", "one")
    assistant.remember_exchange("second", "two")

    assert assistant.history == [
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "two"},
    ]


def test_gemini_assistant_rejects_invalid_intent_json():
    class Interaction:
        output_text = "not json"

    class Interactions:
        def create(self, **kwargs):
            return Interaction()

    class FakeClient:
        interactions = Interactions()

    with pytest.raises(RuntimeError, match="invalid intent JSON"):
        GeminiAssistant(client=FakeClient()).interpret("How are you?")


def test_gemini_assistant_logs_intent_request_and_response(capsys):
    class Interaction:
        output_text = '{"intent":"QUERY","target_agent":null,"instruction":"How are you?","entities":{},"constraints":[],"requires_clarification":false,"clarification_question":null,"confidence":0.91}'

    class Interactions:
        def create(self, **kwargs):
            return Interaction()

    class FakeClient:
        interactions = Interactions()

    GeminiAssistant(client=FakeClient()).interpret("How are you?")

    logs = capsys.readouterr().err
    assert "Gemini intent starting: sent='How are you?'" in logs
    assert "Gemini intent received in" in logs
    assert "received='{\"intent\":\"QUERY\"" in logs
    assert "instructions" not in logs
    assert "schema" not in logs
    assert "recent_conversation" not in logs


def test_gemini_assistant_logs_api_exception(capsys):
    class Interactions:
        def create(self, **kwargs):
            raise TimeoutError("request timed out")

    class FakeClient:
        interactions = Interactions()

    with pytest.raises(TimeoutError, match="request timed out"):
        GeminiAssistant(client=FakeClient()).interpret("How are you?")

    logs = capsys.readouterr().err
    assert "Gemini intent failed after" in logs
    assert "TimeoutError: request timed out" in logs


def test_ollama_assistant_summarizes_agent_result_without_mutating_history():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def chat(self, **kwargs):
            self.calls.append(kwargs)
            return {"message": {"content": "Claude prepared a three-step review plan."}}

    client = FakeClient()
    assistant = OllamaAssistant(client=client)

    reply = assistant.summarize_agent_result(
        "Review authentication",
        "# Plan\n1. Inspect routes\n2. Check sessions\n3. Add tests",
    )

    assert reply == "Claude prepared a three-step review plan."
    assert assistant.history == []
    assert "Summarize the supplied agent result" in client.calls[0]["messages"][0]["content"]
    assert "Review authentication" in client.calls[0]["messages"][1]["content"]
    assert "Inspect routes" in client.calls[0]["messages"][1]["content"]
    assert not client.calls[0]["messages"][0]["content"].startswith("/no_think")


def test_gemini_assistant_summarizes_agent_result_with_concise_logs(capsys):
    class Interaction:
        output_text = "Claude found two authentication issues."

    class Interactions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return Interaction()

    class FakeClient:
        def __init__(self):
            self.interactions = Interactions()

    client = FakeClient()
    assistant = GeminiAssistant(client=client)

    reply = assistant.summarize_agent_result(
        "Review authentication",
        "A sensitive and very long raw result",
    )

    assert reply == "Claude found two authentication issues."
    assert assistant.history == []
    assert "Review authentication" in client.interactions.calls[0]["input"]
    assert "A sensitive and very long raw result" in client.interactions.calls[0]["input"]
    logs = capsys.readouterr().err
    assert "Gemini result synthesis starting" in logs
    assert "Gemini result synthesis received in" in logs
    assert "A sensitive and very long raw result" not in logs


def test_result_synthesis_rejects_empty_agent_result():
    with pytest.raises(ValueError, match="agent result"):
        OllamaAssistant(client=object()).summarize_agent_result("Review", " ")
    with pytest.raises(ValueError, match="agent result"):
        GeminiAssistant(client=object()).summarize_agent_result("Review", " ")
