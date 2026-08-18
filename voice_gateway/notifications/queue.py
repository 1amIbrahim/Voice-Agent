"""Priority-aware notification queue."""

import asyncio
from dataclasses import dataclass, field
from typing import List

from voice_gateway.protocol import Event, Priority


_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}


@dataclass
class NotificationQueue:
    _items: List[Event] = field(default_factory=list)

    def put(self, event: Event) -> None:
        self._items.append(event)
        self._items.sort(key=lambda item: _PRIORITY_ORDER[item.priority])

    def get(self) -> Event:
        if not self._items:
            raise IndexError("notification queue is empty")
        return self._items.pop(0)

    def __len__(self) -> int:
        return len(self._items)

    def pending(self) -> List[Event]:
        return list(self._items)
