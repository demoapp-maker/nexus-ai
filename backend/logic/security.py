"""Small security helpers used by the HTTP layer and outbound tools."""

from __future__ import annotations

import ipaddress
import socket
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, Dict, Iterable
from urllib.parse import urlparse


@dataclass
class SlidingWindowRateLimiter:
    """Process-local rate limiter.

    This is intentionally conservative and dependency-free. It protects a single
    worker from accidental abuse; production deployments should still put a
    shared gateway/rate limiter in front of the service.
    """

    limit: int = 60
    window_seconds: int = 60

    def __post_init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float) -> bool:
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                return False

            events.append(now)
            if len(self._events) > 10_000:
                # Keep the in-process map bounded when callers send many unique
                # client identifiers.
                for stale_key in list(self._events)[:1_000]:
                    if not self._events[stale_key]:
                        self._events.pop(stale_key, None)
            return True


def is_public_hostname(hostname: str) -> bool:
    """Return whether a hostname resolves only to public IP addresses.

    Literal IPs are checked directly. Hostnames are resolved before they are
    fetched so a public-looking hostname cannot point to a private address.
    """

    hostname = (hostname or "").strip().lower().rstrip(".")
    if not hostname or hostname in {"localhost", "localhost.localdomain"}:
        return False

    try:
        addresses: Iterable[str] = [hostname]
        ipaddress.ip_address(hostname)
    except ValueError:
        try:
            addresses = {
                info[4][0]
                for info in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
            }
        except (OSError, socket.gaierror):
            return False

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def validate_public_http_url(url: str) -> str:
    """Validate an outbound URL and return its normalized value."""

    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.hostname or not is_public_hostname(parsed.hostname):
        raise ValueError("The target host is not a public address")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    return value
