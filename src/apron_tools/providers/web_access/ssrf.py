"""SSRF guards for the web_access provider.

Ported verbatim from octonous ``backend/app/services/any_tool/web_access.py``
so that the protections stay identical on both sides of the port.

The guards are load-bearing: ``validate_url`` must be called before any
Tabstack request that accepts a caller-provided URL. Do not trim, simplify,
or "modernise" these checks.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google",
        "169.254.169.254",  # AWS/GCP instance metadata.
    }
)


def _is_private_ip(host: str) -> bool:
    """Return True if *host* resolves to a private/reserved IP address.

    Fails closed: if DNS resolution fails, the host is treated as private
    (unsafe) so that misconfigured or malicious hostnames cannot bypass
    the guard.
    """
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_reserved or addr.is_loopback or addr.is_link_local
    except ValueError:
        pass
    # Hostname — resolve and check every returned address.
    try:
        results = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        return True
    for info in results:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_reserved or addr.is_loopback or addr.is_link_local:
            return True
    return False


def validate_url(url: str) -> str | None:
    """Return an error message if *url* is unsafe, or None if it is OK.

    Rejects non-http(s) schemes, URLs with no hostname, hostnames on the
    blocked list (loopback, cloud metadata), and hostnames that resolve to
    private/reserved/loopback/link-local addresses.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return f"Unsupported URL scheme: {parsed.scheme!r}"

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        return "URL has no hostname"

    if hostname in _BLOCKED_HOSTNAMES:
        return f"Access to {hostname!r} is not allowed"

    if _is_private_ip(hostname):
        return "Access to private/internal network addresses is not allowed"

    return None
