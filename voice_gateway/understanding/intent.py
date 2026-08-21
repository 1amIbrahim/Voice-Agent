"""Structured voice intent models and local understanding adapters."""

import json
import re
import sys
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field, ValidationError


class IntentType(str, Enum):
    COMMAND = "COMMAND"
    QUERY = "QUERY"
    CONFIRMATION = "CONFIRMATION"
    REJECTION = "REJECTION"
    CLARIFICATION = "CLARIFICATION"
    CANCELLATION = "CANCELLATION"
    END_CONVERSATION = "END_CONVERSATION"
    NOTIFICATION_RESPONSE = "NOTIFICATION_RESPONSE"
    CONVERSATION = "CONVERSATION"


class IntentResult(BaseModel):
    intent: IntentType
    target_agent: Optional[str] = None
    instruction: Optional[str] = None
    entities: Dict[str, str] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    acknowledgement: Optional[str] = Field(default=None, max_length=200)
    confidence: float = Field(ge=0, le=1)


class UnderstandingEngine(Protocol):
    def interpret(self, transcript: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        ...


class ConversationEngine(Protocol):
    def respond(self, transcript: str, context: Optional[Dict[str, Any]] = None) -> str:
        ...


class RuleBasedUnderstanding:
    """Deterministic baseline used before a local LLM is connected."""

    _agent_pattern = re.compile(r"\b(claude|codex|gemini|opencode)\b", re.IGNORECASE)

    def interpret(self, transcript: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")

        text = " ".join(transcript.split())
        normalized = text.lower().strip().rstrip(".!?")
        control_text = re.sub(r"[,!?]", "", normalized)
        agent_match = self._agent_pattern.search(text)
        target_agent = agent_match.group(1).lower() if agent_match else None
        if target_agent is None and context:
            active_agent = context.get("active_agent")
            if isinstance(active_agent, str) and active_agent:
                target_agent = active_agent
        entities = {"agent": target_agent} if target_agent else {}

        if self._is_end_conversation(control_text):
            return IntentResult(intent=IntentType.END_CONVERSATION, confidence=0.99)
        if self._is_cancellation(control_text):
            return IntentResult(intent=IntentType.CANCELLATION, confidence=0.99)
        if self._is_confirmation(control_text):
            return IntentResult(intent=IntentType.CONFIRMATION, confidence=0.98)
        if self._is_rejection(control_text):
            return IntentResult(intent=IntentType.REJECTION, confidence=0.98)
        if self._looks_like_command(normalized) or self._looks_like_polite_command(normalized):
            constraints = self._extract_constraints(normalized)
            clarification = self._clarification(text, target_agent, context)
            return IntentResult(
                intent=IntentType.COMMAND,
                target_agent=target_agent,
                instruction=text,
                entities=entities,
                constraints=constraints,
                requires_clarification=clarification is not None,
                clarification_question=clarification,
                confidence=0.82 if clarification is None else 0.55,
            )
        if normalized.endswith("?") or normalized.startswith(("what ", "who ", "where ", "when ", "why ", "how ")):
            return IntentResult(intent=IntentType.QUERY, instruction=text, entities=entities, confidence=0.82)
        if self._contains_command_verb(normalized):
            constraints = self._extract_constraints(normalized)
            clarification = self._clarification(text, target_agent, context)
            return IntentResult(
                intent=IntentType.COMMAND,
                target_agent=target_agent,
                instruction=text,
                entities=entities,
                constraints=constraints,
                requires_clarification=clarification is not None,
                clarification_question=clarification,
                confidence=0.78 if clarification is None else 0.55,
            )
        return IntentResult(intent=IntentType.CONVERSATION, instruction=text, confidence=0.65)

    @staticmethod
    def _is_end_conversation(text: str) -> bool:
        return text in {"end conversation", "end the conversation"}

    @staticmethod
    def _is_cancellation(text: str) -> bool:
        return text in {"stop", "cancel", "cancel that", "never mind", "nevermind"}

    @staticmethod
    def _is_confirmation(text: str) -> bool:
        return text in {"yes", "yes please", "approve", "approved", "allow it", "go ahead"}

    @staticmethod
    def _is_rejection(text: str) -> bool:
        return text in {"no", "no thanks", "reject", "rejected", "don't", "do not"}

    @staticmethod
    def _looks_like_command(text: str) -> bool:
        verbs = (
            "tell ", "ask ", "run ", "open ", "check ", "find ", "create ",
            "delete ", "merge ", "fix ", "review ", "summarize ", "send ",
            "deploy ", "start ", "stop ", "show ", "look ", "explore ",
            "read ", "get ", "explain ", "list ", "inspect ",
        )
        return text.startswith(verbs)

    @staticmethod
    def _looks_like_polite_command(text: str) -> bool:
        return bool(
            re.match(
                r"^(?:can|could|would|will) you\s+"
                r"(?:please\s+)?(?:read|get|explain|explore|check|find|open|run|"
                r"create|delete|merge|fix|review|summarize|send|deploy|show|list|inspect)\b",
                text,
            )
        )

    @staticmethod
    def _contains_command_verb(text: str) -> bool:
        return bool(
            re.search(
                r"\b(delete|merge|fix|review|summarize|check|find|open|run|create|"
                r"send|deploy|explore|read|get|explain|list|inspect)\b",
                text,
            )
        )

    @staticmethod
    def _extract_constraints(text: str) -> List[str]:

        constraints: List[str] = []
        if re.search(r"\b(don't|do not|never)\s+delete\b", text):
            constraints.append("do_not_delete_information")
        if "original" in text and re.search(r"\b(preserve|keep|don't delete|do not delete)\b", text):
            constraints.append("preserve_original_files")
        if "only" in text:
            constraints.append("only_requested_scope")
        return constraints

    @staticmethod
    def _clarification(
        transcript: str,
        target_agent: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if re.search(r"\b(it|that|there)\b", transcript.lower()) and not context:
            return "What should I apply that to?"
        if transcript.lower().startswith("tell it") and not target_agent and not context:
            return "Which agent should I tell?"
        return None


class OllamaAssistant:
    """One stateful local model for intent understanding and conversation."""

    INTENT_SYSTEM_PROMPT = """/no_think

You are the intent router for a local conversational assistant. Classify the
current user transcript and return only JSON matching the requested schema.

COMMAND means the user wants an agent to perform an action. Imperative requests
such as “Explore the directory” and polite requests such as “Can you read the
README file?” are COMMAND. Preserve the user's requested scope, negation,
constraints, entities, and desired outcome in a concise agent-facing instruction.

QUERY and CONVERSATION are for replies the assistant can answer without an
agent. CONFIRMATION, REJECTION, CANCELLATION, and END_CONVERSATION are reserved
for explicit control phrases and must never be inferred from unrelated requests.
Use requires_clarification=true only when missing information could cause the
agent to perform the wrong action. For COMMAND intents, include an acknowledgement
that a composed Jarvis-like assistant can speak immediately while the agent works.
Keep it to one brief sentence, confirm only that work is starting, and never claim
completion or invent facts. For non-COMMAND intents, set acknowledgement to null.
Use supplied context and recent conversation only to resolve references; never
invent facts, paths, actions, or task state. Do not execute commands or call tools."""

    CONVERSATION_SYSTEM_PROMPT = """You are the conversational voice of a local
personal assistant. Speak naturally, calmly, and concisely. Your manner is
capable, composed, respectful, and subtly warm. Address the user as “sir”
occasionally when natural, but not in every response.

Another component enforces safety and dispatches commands. Never execute tools,
reinterpret permissions, or claim an action occurred unless conversation history
or supplied context explicitly contains a completed result.

Use one to three short, speech-friendly sentences in plain language without
Markdown, lists, code, URLs, or headings. Use context only to resolve relevant
references. Never invent progress, files, results, agent activity, or system
state. If uncertain, say so briefly. Do not add a generic follow-up question;
the voice gateway handles follow-ups."""

    def __init__(
        self,
        model: str = "qwen3:4b",
        client: Any = None,
        max_history_messages: int = 12,
    ) -> None:
        if not model:
            raise ValueError("model must not be empty")
        if max_history_messages <= 0:
            raise ValueError("max_history_messages must be greater than zero")
        self.model = model
        self._client = client
        self.max_history_messages = max_history_messages
        self._history: List[Dict[str, str]] = []

    @property
    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from ollama import Client
        except ImportError as exc:
            raise RuntimeError(
                "Ollama assistant requires the optional 'ollama' package"
            ) from exc
        self._client = Client()
        return self._client

    def interpret(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        deterministic = RuleBasedUnderstanding().interpret(transcript, context)
        control_intents = {
            IntentType.CONFIRMATION,
            IntentType.REJECTION,
            IntentType.CANCELLATION,
            IntentType.END_CONVERSATION,
        }
        if deterministic.intent in control_intents:
            return deterministic

        response = self._get_client().chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.INTENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._intent_prompt(transcript, context),
                },
            ],
            format=IntentResult.model_json_schema(),
        )
        content = response["message"]["content"]
        self._log_raw_response(content)
        try:
            result = IntentResult.model_validate_json(self._extract_json(content))
        except (ValidationError, ValueError, TypeError) as exc:
            raise RuntimeError(
                f"understanding model returned invalid intent JSON: {content!r}"
            ) from exc
        if result.intent in control_intents:
            self._log_raw_response(
                f"ignored non-explicit {result.intent.value}; using deterministic interpretation"
            )
            return deterministic
        if deterministic.intent is IntentType.COMMAND and result.intent is not IntentType.COMMAND:
            self._log_raw_response(
                f"ignored {result.intent.value} for explicit command; using deterministic interpretation"
            )
            return deterministic
        return result

    def respond(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        messages = [
            {"role": "system", "content": self.CONVERSATION_SYSTEM_PROMPT},
            *self._history,
            {
                "role": "user",
                "content": json.dumps(
                    {"transcript": transcript, "context": context or {}},
                    ensure_ascii=False,
                ),
            },
        ]
        response = self._get_client().chat(model=self.model, messages=messages)
        content = response.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("conversation model returned an empty response")
        reply = content.strip()
        self.remember_exchange(transcript, reply)
        return reply

    def remember_exchange(self, user_text: str, assistant_text: str) -> None:
        if not user_text.strip() or not assistant_text.strip():
            return
        self._history.extend(
            [
                {"role": "user", "content": user_text.strip()[:1000]},
                {"role": "assistant", "content": assistant_text.strip()[:2000]},
            ]
        )
        self._history = self._history[-self.max_history_messages :]

    def _intent_prompt(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        return json.dumps(
            {
                "task": "Interpret the current transcript without executing it.",
                "transcript": transcript,
                "context": context or {},
                "recent_conversation": self._history,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _log_raw_response(content: Any) -> None:
        message = f"[voice-gateway] understanding raw response: {content!r}"
        for stream in (sys.stderr, sys.stdout):
            try:
                print(message, file=stream, flush=True)
                return
            except (OSError, ValueError):
                continue

    @staticmethod
    def _extract_json(content: str) -> str:
        text = content.strip()
        if text.startswith("```") and text.endswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, count=1).removesuffix("```").strip()
        return text


class GeminiAssistant:
    """One stateful Gemini model for intent understanding and conversation."""

    INTENT_SYSTEM_PROMPT = """You are the intent router for a conversational
assistant. Return only JSON matching the supplied schema. Do not include
reasoning, commentary, or Markdown.

COMMAND means the user wants an agent to perform an action. Imperative requests
such as “Explore the directory” and polite requests such as “Can you read the
README file?” are COMMAND. Preserve the user's requested scope, negation,
constraints, entities, and desired outcome in a concise agent-facing instruction.

QUERY and CONVERSATION are for replies the assistant can answer without an
agent. CONFIRMATION, REJECTION, CANCELLATION, and END_CONVERSATION are reserved
for explicit control phrases and must never be inferred from unrelated requests.
Use requires_clarification=true only when missing information could cause the
agent to perform the wrong action. For COMMAND intents, include an acknowledgement
that a composed Jarvis-like assistant can speak immediately while the agent works.
Keep it to one brief sentence, confirm only that work is starting, and never claim
completion or invent facts. For non-COMMAND intents, set acknowledgement to null.
Use supplied context and recent conversation only to resolve references; never
invent facts, paths, actions, or task state. Do not execute commands or call tools."""

    CONVERSATION_SYSTEM_PROMPT = """You are the conversational voice of a personal
assistant. Speak naturally, calmly, and concisely. Your manner is capable,
composed, respectful, and subtly warm. Address the user as “sir” occasionally
when natural, but not in every response.

Another component enforces safety and dispatches commands. Never execute tools,
reinterpret permissions, or claim an action occurred unless conversation history
or supplied context explicitly contains a completed result.

Use one to three short, speech-friendly sentences in plain language without
Markdown, lists, code, URLs, or headings. Use context only to resolve relevant
references. Never invent progress, files, results, agent activity, or system
state. If uncertain, say so briefly. Do not add a generic follow-up question;
the voice gateway handles follow-ups."""

    def __init__(
        self,
        model: str = "gemini-3.7-flash",
        client: Any = None,
        max_history_messages: int = 12,
    ) -> None:
        if not model:
            raise ValueError("model must not be empty")
        if max_history_messages <= 0:
            raise ValueError("max_history_messages must be greater than zero")
        self.model = model
        self._client = client
        self.max_history_messages = max_history_messages
        self._history: List[Dict[str, str]] = []

    @property
    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._log("creating Gemini client")
        try:
            from google import genai

            self._client = genai.Client()
        except Exception as exc:
            self._log_exception("client creation", exc)
            if isinstance(exc, ImportError):
                raise RuntimeError(
                    "Gemini assistant requires the optional 'google-genai' package"
                ) from exc
            raise
        self._log("Gemini client created")
        return self._client

    def interpret(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        deterministic = RuleBasedUnderstanding().interpret(transcript, context)
        control_intents = {
            IntentType.CONFIRMATION,
            IntentType.REJECTION,
            IntentType.CANCELLATION,
            IntentType.END_CONVERSATION,
        }
        if deterministic.intent in control_intents:
            self._log(
                f"Gemini intent request skipped for deterministic "
                f"{deterministic.intent.value} control"
            )
            return deterministic

        request = self._intent_prompt(transcript, context)
        self._log_request("intent", transcript)
        started_at = time.perf_counter()
        try:
            interaction = self._get_client().interactions.create(
                model=self.model,
                input=request,
            )
            content = self._output_text(interaction)
        except Exception as exc:
            self._log_exception("intent", exc, started_at)
            raise
        self._log_response("intent", content, started_at)
        try:
            result = IntentResult.model_validate_json(self._extract_json(content))
        except (ValidationError, ValueError, TypeError) as exc:
            raise RuntimeError(
                f"understanding model returned invalid intent JSON: {content!r}"
            ) from exc
        if result.intent in control_intents:
            self._log_raw_response(
                f"ignored non-explicit {result.intent.value}; using deterministic interpretation"
            )
            return deterministic
        if deterministic.intent is IntentType.COMMAND and result.intent is not IntentType.COMMAND:
            self._log_raw_response(
                f"ignored {result.intent.value} for explicit command; using deterministic interpretation"
            )
            return deterministic
        return result

    def respond(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        request = json.dumps(
            {
                "instructions": self.CONVERSATION_SYSTEM_PROMPT,
                "recent_conversation": self._history,
                "transcript": transcript,
                "context": context or {},
            },
            ensure_ascii=False,
        )
        self._log_request("conversation", transcript)
        started_at = time.perf_counter()
        try:
            interaction = self._get_client().interactions.create(
                model=self.model,
                input=request,
            )
            reply = self._output_text(interaction).strip()
        except Exception as exc:
            self._log_exception("conversation", exc, started_at)
            raise
        self._log_response("conversation", reply, started_at)
        if not reply:
            raise RuntimeError("conversation model returned an empty response")
        self.remember_exchange(transcript, reply)
        return reply

    def remember_exchange(self, user_text: str, assistant_text: str) -> None:
        if not user_text.strip() or not assistant_text.strip():
            return
        self._history.extend(
            [
                {"role": "user", "content": user_text.strip()[:1000]},
                {"role": "assistant", "content": assistant_text.strip()[:2000]},
            ]
        )
        self._history = self._history[-self.max_history_messages :]

    def _intent_prompt(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        return json.dumps(
            {
                "instructions": self.INTENT_SYSTEM_PROMPT,
                "schema": IntentResult.model_json_schema(),
                "task": "Interpret the current transcript without executing it.",
                "transcript": transcript,
                "context": context or {},
                "recent_conversation": self._history,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _output_text(interaction: Any) -> str:
        content = getattr(interaction, "output_text", None)
        if not isinstance(content, str):
            raise RuntimeError("Gemini returned an invalid response")
        return content

    def _log_request(self, operation: str, transcript: str) -> None:
        self._log(f"Gemini {operation} starting: sent={transcript!r}")

    def _log_response(
        self,
        operation: str,
        content: str,
        started_at: float,
    ) -> None:
        elapsed = time.perf_counter() - started_at
        self._log(
            f"Gemini {operation} received in {elapsed:.2f}s: received={content!r}"
        )

    def _log_exception(
        self,
        operation: str,
        exc: Exception,
        started_at: Optional[float] = None,
    ) -> None:
        elapsed = ""
        if started_at is not None:
            elapsed = f" after {time.perf_counter() - started_at:.2f}s"
        self._log(
            f"Gemini {operation} failed{elapsed}: "
            f"{type(exc).__name__}: {exc}"
        )

    @staticmethod
    def _log(message: str) -> None:
        formatted = f"[voice-gateway] {message}"
        for stream in (sys.stderr, sys.stdout):
            try:
                print(formatted, file=stream, flush=True)
                return
            except (OSError, ValueError):
                continue

    @staticmethod
    def _log_raw_response(content: Any) -> None:
        GeminiAssistant._log(f"understanding raw response: {content!r}")

    @staticmethod
    def _extract_json(content: str) -> str:
        text = content.strip()
        if text.startswith("```") and text.endswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, count=1).removesuffix("```").strip()
        return text
