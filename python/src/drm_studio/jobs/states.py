from __future__ import annotations

from enum import Enum


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


__all__ = ["JobState"]
