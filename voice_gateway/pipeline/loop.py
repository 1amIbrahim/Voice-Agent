"""Composable local voice-to-agent pipeline."""

from dataclasses import dataclass, field
import sys
from typing import Any, Dict, List, Optional

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
        session_id: str = "voice_session_01",
        session_context: Optional[SessionContext] = None,
        authorization_policy: Optional[AuthorizationPolicy] = None,
    ) -> None:
        self.understanding = understanding or RuleBasedUnderstanding()
        self.agent_platform = agent_platform or FakeAgentPlatform()
        self.response_formatter = response_formatter or ResponseFormatter()
        self.session_id = session_id
        self.session_context = session_context or SessionContext()
        self.authorization_policy = authorization_policy or AuthorizationPolicy()

    async def process_transcript(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
        detail: DetailLevel = DetailLevel.NORMAL,
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
        if intent.intent is IntentType.CONFIRMATION:
            _log("confirmation received; checking for a pending command")
            return await self._approve_pending_confirmation(detail)
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
            return PipelineResult(command=command)

        command = user_command(
            UserCommand(
                intent="delegate_task",
                instruction=intent.instruction or transcript,
                target=intent.target_agent,
                constraints=intent.constraints,
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
        return await self._dispatch(command, detail)

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

    async def _approve_pending_confirmation(
        self,
        detail: DetailLevel,
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
        result = await self._dispatch(pending.command, detail)
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
    ) -> PipelineResult:
        _log(
            "dispatching command: "
            f"target={command.content.get('target') or 'default'}, "
            f"backend={type(self.agent_platform).__name__}"
        )
        self.session_context.remember_command(command)
        agent_events = [event async for event in self.agent_platform.dispatch(command)]
        _log(
            "agent lifecycle events: "
            f"{', '.join(event.event.value for event in agent_events) or 'none'}"
        )
        responses = [
            response
            for event in agent_events
            if (response := self.response_formatter.format(event, detail)) is not None
        ]
        _log(f"formatted agent responses: {len(responses)}")
        return PipelineResult(
            command=command,
            agent_events=agent_events,
            responses=responses,
        )
