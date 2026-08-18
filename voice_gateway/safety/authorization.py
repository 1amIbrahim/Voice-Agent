"""Authorization rules for commands that need explicit approval."""

from typing import Iterable

from voice_gateway.protocol import Event


class AuthorizationPolicy:
    _sensitive_verbs = (
        "delete",
        "deploy",
        "install",
        "push",
        "send",
        "publish",
        "remove",
        "drop",
        "shutdown",
    )

    def requires_confirmation(self, command: Event) -> bool:
        instruction = command.content.get("instruction", "")
        if not isinstance(instruction, str):
            return False
        normalized = instruction.lower()
        return any(self._contains_verb(normalized, verb) for verb in self._sensitive_verbs)

    @staticmethod
    def _contains_verb(instruction: str, verb: str) -> bool:
        return f"{verb} " in instruction or instruction.startswith(verb)

    @staticmethod
    def confirmation_message(command: Event) -> str:
        instruction = command.content.get("instruction", "this action")
        return f"I need your confirmation before I {instruction}. Should I continue?"
