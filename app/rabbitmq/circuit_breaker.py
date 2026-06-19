import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    provider: str
    failure_threshold: int = 5          # failures before opening
    success_threshold: int = 2          # successes in HALF_OPEN before closing
    timeout_seconds: float = 60.0       # time in OPEN before HALF_OPEN
    window_seconds: float = 60.0        # sliding window for failure counting

    # Internal state
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    opened_at: float = field(default=0.0, init=False)
    _failure_timestamps: list = field(default_factory=list, init=False)

    def is_open(self) -> bool:
        """Returns True if requests should be blocked."""
        if self.state == CircuitState.CLOSED:
            return False
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.timeout_seconds:
                self._transition_to_half_open()
                return False
            return True
        return False  # HALF_OPEN allows one test request

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self._cleanup_old_failures()

    def record_failure(self) -> None:
        now = time.monotonic()
        self._failure_timestamps.append(now)
        self._cleanup_old_failures()
        self.failure_count = len(self._failure_timestamps)
        self.last_failure_time = now

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = time.monotonic()
        self.success_count = 0
        logger.warning(
            "circuit_breaker_opened",
            provider=self.provider,
            failure_count=self.failure_count,
        )

    def _transition_to_half_open(self) -> None:
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info("circuit_breaker_half_open", provider=self.provider)

    def _transition_to_closed(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self._failure_timestamps.clear()
        logger.info("circuit_breaker_closed", provider=self.provider)

    def _cleanup_old_failures(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        self._failure_timestamps = [t for t in self._failure_timestamps if t > cutoff]

    def get_status(self) -> dict:
        return {
            "provider": self.provider,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


# ── Global circuit breaker registry ──────────────────────────────────────────
_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker(provider=provider)
    return _breakers[provider]


def get_all_circuit_breaker_statuses() -> list[dict]:
    return [b.get_status() for b in _breakers.values()]
