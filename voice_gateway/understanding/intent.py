"""Structured voice intent models and local understanding adapters."""

import json
import re
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
    confidence: float = Field(ge=0, le=1)


class UnderstandingEngine(Protocol):
    def interpret(self, transcript: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
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
        entities = {"agent": target_agent} if target_agent else {}

        if self._is_cancellation(control_text):
            return IntentResult(intent=IntentType.CANCELLATION, confidence=0.99)
        if self._is_confirmation(control_text):
            return IntentResult(intent=IntentType.CONFIRMATION, confidence=0.98)
        if self._is_rejection(control_text):
            return IntentResult(intent=IntentType.REJECTION, confidence=0.98)
        if normalized.endswith("?") or normalized.startswith(("what ", "who ", "where ", "when ", "why ", "how ")):
            return IntentResult(intent=IntentType.QUERY, instruction=text, entities=entities, confidence=0.82)
        if self._looks_like_command(normalized) or self._contains_command_verb(normalized):
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
            "deploy ", "start ", "stop ", "show ", "look ",
        )
        return text.startswith(verbs)

    @staticmethod
    def _contains_command_verb(text: str) -> bool:
        return bool(re.search(r"\b(delete|merge|fix|review|summarize|check|find|open|run|create|send|deploy)\b", text))

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


class OllamaUnderstanding:
    """Optional Ollama adapter for a local structured-output model."""

    def __init__(self, model: str = "qwen2.5:3b", client: Any = None) -> None:
        if not model:
            raise ValueError("model must not be empty")
        self.model = model
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from ollama import Client
        except ImportError as exc:
            raise RuntimeError(
                "Ollama understanding requires the optional 'ollama' package"
            ) from exc
        self._client = Client()
        return self._client

    def interpret(self, transcript: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        client = self._get_client()
        prompt = self._prompt(transcript, context)
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format=IntentResult.model_json_schema(),
        )
        content = response["message"]["content"]
        try:
            return IntentResult.model_validate_json(content)
        except (ValidationError, ValueError, TypeError) as exc:
            raise RuntimeError("understanding model returned invalid intent JSON") from exc

    @staticmethod
    def _prompt(transcript: str, context: Optional[Dict[str, Any]]) -> str:
        return json.dumps(
            {
                "task": "Interpret the transcript without executing it.",
                "rules": [
                    "Preserve negation, constraints, scope, and user intent.",
                    "Do not invent agents, paths, actions, or facts.",
                    "Set requires_clarification when ambiguity could change execution.",
                    "Return only the requested JSON schema.",
                ],
                "transcript": transcript,
                "context": context or {},
            }
        )
