"""Composable local voice-to-agent pipeline."""

import asyncio
from dataclasses import dataclass, field
import sys
from typing import Any, Callable, Dict, List, Optional

from voice_gateway.context import PendingConfirmation, SessionContext
from voice_gateway.protocol import Event, EventType, UserCommand, user_command
from voice_gateway.response import DetailLevel, ResponseFormatter
from voice_gateway.routing import FakeAgentPlatform
from voice_gateway.safety import AuthorizationPolicy
from voice_gateway.understanding import IntentType, RuleBasedUnderstanding


def _log(message: str) -> None:
    formatted = f"[voice-gateway] {message}"
    for stream in (sys.stderr, sys.stdout):
        try:
            print(formatted, file=stream, flush=True)
            return
        except (OSError, ValueError):
            continue


def _log_intent_check(transcript: str) -> None:
    _log(f"checking intent for: {transcript!r}")


@dataclass
class PipelineResult:
    command: Event
    agent_events: List[Event] = field(default_factory=list)
    responses: List[str] = field(default_factory=list)


class VoicePipeline:
    def __init__(
        self,
        understanding: Optional[Any] = None,
        agent_platform: Optional[Any] = None,
        response_formatter: Optional[ResponseFormatter] = None,
        conversation_engine: Optional[Any] = None,
        session_id: str = "voice_session_01",
        session_context: Optional[SessionContext] = None,
        authorization_policy: Optional[AuthorizationPolicy] = None,
    ) -> None:
        self.understanding = understanding or RuleBasedUnderstanding()
        self.agent_platform = agent_platform or FakeAgentPlatform()
        self.response_formatter = response_formatter or ResponseFormatter()
        self.conversation_engine = conversation_engine or (
            self.understanding
            if callable(getattr(self.understanding, "respond", None))
            else None
        )
        self.session_id = session_id
        self.session_context = session_context or SessionContext()
        self.authorization_policy = authorization_policy or AuthorizationPolicy()

    async def process_transcript(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
        detail: DetailLevel = DetailLevel.NORMAL,
        on_agent_started: Optional[Callable[[Event], None]] = None,
    ) -> PipelineResult:
        _log_intent_check(transcript)
        intent = self.understanding.interpret(
            transcript,
            self._interpretation_context(context),
        )
        _log(
            "intent result: "
            f"intent={intent.intent.value}, target={intent.target_agent or 'none'}, "
            f"clarification={intent.requires_clarification}, confidence={intent.confidence:.2f}"
        )
        if intent.intent is IntentType.END_CONVERSATION:
            _log("conversation exit received; dispatch skipped")
            return self._conversation_exit_result()
        if intent.intent is IntentType.STANDBY:
            _log("standby received; dispatch skipped")
            return self._standby_result()
        if intent.intent is IntentType.CONFIRMATION:
            _log("confirmation received; checking for a pending command")
            return await self._approve_pending_confirmation(detail, on_agent_started)
        if intent.intent in (IntentType.REJECTION, IntentType.CANCELLATION):
            _log(f"{intent.intent.value.lower()} received; clearing any pending command")
            return self._reject_pending_confirmation(intent.intent)
        if intent.requires_clarification:
            _log("request requires clarification; dispatch skipped")
            return self._clarification_result(
                intent.clarification_question or "Please clarify."
            )
        if intent.intent is not IntentType.COMMAND:
            _log(f"intent {intent.intent.value} is not dispatchable; agent not started")
            command = user_command(
                UserCommand(
                    intent=intent.intent.value,
                    instruction=intent.instruction or transcript,
                ),
                session_id=self.session_id,
            )
            if self.conversation_engine is None:
                return PipelineResult(command=command)
            reply = self.conversation_engine.respond(
                transcript,
                self._interpretation_context(context),
            )
            return PipelineResult(command=command, responses=[reply])

        command = user_command(
            UserCommand(
                intent="delegate_task",
                instruction=intent.instruction or transcript,
                target=intent.target_agent,
                constraints=intent.constraints,
                acknowledgement=intent.acknowledgement,
            ),
            session_id=self.session_id,
        )
        if self.authorization_policy.requires_confirmation(command):
            _log("command requires confirmation; agent dispatch deferred")
            command = command.model_copy(
                update={
                    "content": {
                        **command.content,
                        "requires_confirmation": True,
                    }
                }
            )
            message = self.authorization_policy.confirmation_message(command)
            self.session_context.pending_confirmation = PendingConfirmation(
                command=command,
                message=message,
            )
            return PipelineResult(command=command, responses=[message])
        return await self._dispatch(command, detail, on_agent_started)

    def _interpretation_context(
        self,
        supplied_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            **self.session_context.interpretation_context(),
            **(supplied_context or {}),
        }

    def _clarification_result(self, message: str) -> PipelineResult:
        command = user_command(
            UserCommand(intent=IntentType.CLARIFICATION.value, instruction=message),
            session_id=self.session_id,
        )
        return PipelineResult(command=command, responses=[message])

    def _conversation_exit_result(self) -> PipelineResult:
        command = user_command(
            UserCommand(
                intent=IntentType.END_CONVERSATION.value,
                instruction="end conversation",
            ),
            session_id=self.session_id,
        )
        return PipelineResult(command=command, responses=["Conversation ended. Goodbye."])

    def _standby_result(self) -> PipelineResult:
        command = user_command(
            UserCommand(
                intent=IntentType.STANDBY.value,
                instruction="stand by",
            ),
            session_id=self.session_id,
        )
        return PipelineResult(command=command)

    async def _approve_pending_confirmation(
        self,
        detail: DetailLevel,
        on_agent_started: Optional[Callable[[Event], None]] = None,
    ) -> PipelineResult:
        pending = self.session_context.pending_confirmation
        if pending is None:
            return self._clarification_result("What action should I approve?")
        decision = Event(
            event=EventType.USER_CONFIRMATION,
            source="voice",
            session_id=self.session_id,
            correlation_id=pending.command.id,
            content={"decision": "approved"},
        )
        self.session_context.pending_confirmation = None
        result = await self._dispatch(pending.command, detail, on_agent_started)
        return PipelineResult(
            command=decision,
            agent_events=result.agent_events,
            responses=result.responses,
        )

    def _reject_pending_confirmation(self, intent: IntentType) -> PipelineResult:
        pending = self.session_context.pending_confirmation
        event_type = (
            EventType.USER_CANCELLATION
            if intent is IntentType.CANCELLATION
            else EventType.USER_REJECTION
        )
        decision = Event(
            event=event_type,
            source="voice",
            session_id=self.session_id,
            correlation_id=pending.command.id if pending else None,
            content={"decision": intent.value.lower()},
        )
        self.session_context.pending_confirmation = None
        message = "The pending action was cancelled." if pending else "There is no pending action."
        return PipelineResult(command=decision, responses=[message])

    async def _dispatch(
        self,
        command: Event,
        detail: DetailLevel,
        on_agent_started: Optional[Callable[[Event], None]] = None,
    ) -> PipelineResult:
        _log(
            "dispatching command: "
            f"target={command.content.get('target') or 'default'}, "
            f"backend={type(self.agent_platform).__name__}"
        )
        self.session_context.remember_command(command)
        agent_events: List[Event] = []
        responses: List[str] = []
        instruction = str(command.content.get("instruction", ""))
        async for event in self.agent_platform.dispatch(command):
            agent_events.append(event)
            if event.event is EventType.AGENT_STARTED and on_agent_started is not None:
                on_agent_started(event)
            if event.event is EventType.AGENT_PROGRESS:
                self._log_agent_progress(event)
                continue
            response = None
            if event.event is EventType.AGENT_COMPLETED:
                result = event.content.get("message")
                summarize = getattr(
                    self.conversation_engine,
                    "summarize_agent_result",
                    None,
                )
                if callable(summarize) and isinstance(result, str) and result.strip():
                    try:
                        response = await asyncio.to_thread(
                            summarize,
                            instruction,
                            result,
                            self.session_context.interpretation_context(),
                        )
                    except Exception as exc:
                        _log(f"agent result synthesis failed; using fallback: {exc}")
            if response is None:
                response = self.response_formatter.format(event, detail)
            if response is not None:
                responses.append(response)
        _log(
            "agent lifecycle events: "
            f"{', '.join(event.event.value for event in agent_events) or 'none'}"
        )
        _log(f"formatted agent responses: {len(responses)}")
        remember_exchange = getattr(self.conversation_engine, "remember_exchange", None)
        if callable(remember_exchange) and responses:
            remember_exchange(instruction, " ".join(responses))
        return PipelineResult(
            command=command,
            agent_events=agent_events,
            responses=responses,
        )

    @staticmethod
    def _log_agent_progress(event: Event) -> None:
        message = event.content.get("message", "Claude Code is working")
        elapsed = event.content.get("elapsed_seconds")
        usage = event.content.get("usage")
        suffix = f" ({elapsed:.1f}s)" if isinstance(elapsed, (int, float)) else ""
        if isinstance(usage, dict):
            output_tokens = usage.get("output_tokens")
            if isinstance(output_tokens, int) and output_tokens > 0:
                suffix += f" [{output_tokens} output tokens]"
        _log(f"Claude Code progress: {message}{suffix}")
