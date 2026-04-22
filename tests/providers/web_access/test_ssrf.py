"""Tests for SSRF guards used by the web_access provider."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apron_tools.providers.web_access.ssrf import (
    _BLOCKED_HOSTNAMES,
    _is_private_ip,
    validate_url,
)


class TestBlockedHostnames:
    """The blocked-hostnames frozenset must cover loopback and cloud metadata."""

    def test_contains_localhost(self):
        assert "localhost" in _BLOCKED_HOSTNAMES

    def test_contains_aws_gcp_imds(self):
        assert "169.254.169.254" in _BLOCKED_HOSTNAMES

    def test_contains_google_metadata_hostnames(self):
        assert "metadata.google.internal" in _BLOCKED_HOSTNAMES
        assert "metadata.google" in _BLOCKED_HOSTNAMES


class TestIsPrivateIp:
    """_is_private_ip must classify literal addresses and resolved hosts."""

    def test_loopback_literal(self):
        assert _is_private_ip("127.0.0.1") is True

    def test_private_literal_rfc1918(self):
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("172.16.0.1") is True

    def test_link_local_literal(self):
        assert _is_private_ip("169.254.169.254") is True

    def test_ipv6_loopback_literal(self):
        assert _is_private_ip("::1") is True

    def test_public_ip_literal(self):
        # 8.8.8.8 is Google Public DNS — always a public address.
        assert _is_private_ip("8.8.8.8") is False

    def test_unresolvable_host_fails_closed(self):
        # Fail-closed: unresolvable hostnames must be treated as private.
        with patch(
            "apron_tools.providers.web_access.ssrf.socket.getaddrinfo",
            side_effect=OSError("no dns"),
        ):
            assert _is_private_ip("this-host-does-not-exist.invalid") is True

    def test_hostname_resolves_to_private(self):
        fake_result = [(0, 0, 0, "", ("10.0.0.5", 0))]
        with patch(
            "apron_tools.providers.web_access.ssrf.socket.getaddrinfo",
            return_value=fake_result,
        ):
            assert _is_private_ip("internal.example") is True

    def test_hostname_resolves_to_public(self):
        fake_result = [(0, 0, 0, "", ("93.184.216.34", 0))]
        with patch(
            "apron_tools.providers.web_access.ssrf.socket.getaddrinfo",
            return_value=fake_result,
        ):
            assert _is_private_ip("example.com") is False


class TestValidateUrl:
    """validate_url must reject unsafe URLs and accept valid public ones."""

    def test_rejects_localhost(self):
        assert validate_url("http://localhost/x") is not None
        assert validate_url("http://localhost:8080/") is not None

    def test_rejects_aws_imds(self):
        assert validate_url("http://169.254.169.254/latest/meta-data/") is not None

    def test_rejects_gcp_metadata(self):
        assert validate_url("http://metadata.google.internal/computeMetadata/v1/") is not None

    def test_rejects_private_ipv4_literal(self):
        assert validate_url("http://10.0.0.1/") is not None
        assert validate_url("http://192.168.1.1/") is not None

    def test_rejects_link_local(self):
        # 169.254.0.0/16 is link-local — matches the frozenset entry and also
        # the _is_private_ip link-local check for any other address in range.
        assert validate_url("http://169.254.1.1/") is not None

    def test_rejects_non_http_scheme(self):
        assert validate_url("file:///etc/passwd") is not None
        assert validate_url("ftp://example.com/") is not None
        assert validate_url("javascript:alert(1)") is not None

    def test_rejects_empty_hostname(self):
        assert validate_url("http:///") is not None

    @pytest.mark.parametrize("url", ["http://", "://", ""])
    def test_rejects_malformed(self, url: str) -> None:
        assert validate_url(url) is not None

    def test_rejects_trailing_dot_localhost(self):
        # A trailing dot in the host must not bypass the blocklist.
        assert validate_url("http://localhost./") is not None

    def test_accepts_valid_public_url(self):
        fake_result = [(0, 0, 0, "", ("93.184.216.34", 0))]
        with patch(
            "apron_tools.providers.web_access.ssrf.socket.getaddrinfo",
            return_value=fake_result,
        ):
            assert validate_url("https://example.com/") is None

    def test_unresolvable_public_like_host_blocked(self):
        # Fail-closed path must apply to validate_url through _is_private_ip.
        with patch(
            "apron_tools.providers.web_access.ssrf.socket.getaddrinfo",
            side_effect=OSError("no dns"),
        ):
            assert validate_url("http://this-host-does-not-exist.invalid/") is not None
