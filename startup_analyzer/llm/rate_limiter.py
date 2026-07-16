"""Sliding-window rate limiter for Gemini API calls."""
from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiterMetrics:
    calls_made: int = 0
    total_wait_seconds: float = 0.0
    calls_throttled: int = 0
    max_rpm: int = 20


class SlidingWindowRateLimiter:
    """Enforces a maximum number of calls per rolling 60-second window."""

    def __init__(self, max_rpm: int = 20, window_seconds: float = 60.0):
        self.max_rpm = max_rpm
        self.window_seconds = window_seconds
        self._timestamps: list[float] = []
        self._lock = threading.Lock()
        self.metrics = RateLimiterMetrics(max_rpm=max_rpm)

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self.max_rpm:
                wait_until = self._timestamps[0] + self.window_seconds
                wait_seconds = max(0.0, wait_until - now)
                if wait_seconds > 0:
                    self.metrics.calls_throttled += 1
                    self.metrics.total_wait_seconds += wait_seconds
                    print(
                        f"[gemini] rate limit: waiting {wait_seconds:.1f}s "
                        f"({len(self._timestamps)}/{self.max_rpm} calls in window)",
                        file=sys.stderr,
                    )
                    time.sleep(wait_seconds)
                    now = time.monotonic()
                    cutoff = now - self.window_seconds
                    self._timestamps = [t for t in self._timestamps if t > cutoff]

            self._timestamps.append(time.monotonic())
            self.metrics.calls_made += 1

    def snapshot(self) -> RateLimiterMetrics:
        with self._lock:
            return RateLimiterMetrics(
                calls_made=self.metrics.calls_made,
                total_wait_seconds=round(self.metrics.total_wait_seconds, 2),
                calls_throttled=self.metrics.calls_throttled,
                max_rpm=self.max_rpm,
            )
