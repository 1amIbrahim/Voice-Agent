"""Composable local voice-to-agent pipeline."""

from dataclasses import dataclass, field
import sys
from typing import Any, AsyncIterator, Dict, List, Optional

from voice_gateway.protocol import Event, EventType, UserCommand, user_command
from voice_gateway.response import DetailLevel, ResponseFormatter
from voice_gateway.routing import FakeAgentPlatform
from voice_gateway.understanding import IntentType, RuleBasedUnderstanding


def _log_intent_check(transcript: str) -> None:
    message = f"[voice-gateway] checking intent for: {transcript!r}"
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        try:
            print(message, file=sys.stdout, flush=True)
        except OSError:
            pass


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
    ) -> None:
        self.understanding = understanding or RuleBasedUnderstanding()
        self.agent_platform = agent_platform or FakeAgentPlatform()
        self.response_formatter = response_formatter or ResponseFormatter()
        self.session_id = session_id

    async def process_transcript(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
        detail: DetailLevel = DetailLevel.NORMAL,
    ) -> PipelineResult:
        _log_intent_check(transcript)
        intent = self.understanding.interpret(transcript, context)
        if intent.requires_clarification:
            command = user_command(
                UserCommand(
                    intent=IntentType.CLARIFICATION.value,
                    instruction=intent.clarification_question or "Please clarify.",
                ),
                session_id=self.session_id,
            )
            return PipelineResult(
                command=command,
                responses=[intent.clarification_question or "Please clarify."],
            )

        if intent.intent is not IntentType.COMMAND:
            command = user_command(
                UserCommand(intent=intent.intent.value, instruction=intent.instruction or transcript),
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
        agent_events = [event async for event in self.agent_platform.dispatch(command)]
        responses = [
            response
            for event in agent_events
            if (response := self.response_formatter.format(event, detail)) is not None
        ]
        return PipelineResult(command=command, agent_events=agent_events, responses=responses)
