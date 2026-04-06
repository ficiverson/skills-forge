"""Tests for the HttpPackFetcher adapter using a fake URL opener."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from skill_forge.infrastructure.adapters.http_pack_fetcher import (
    DEFAULT_MAX_BYTES,
    FetchTooLargeError,
    HttpPackFetcher,
)


class _FakeResponse:
    def __init__(self, payload: bytes, content_length: int | None = None) -> None:
        self._buf = io.BytesIO(payload)
        self._content_length = (
            content_length if content_length is not None else len(payload)
        )

    def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)

    def getheader(self, name: str) -> str | None:
        if name.lower() == "content-length":
            return str(self._content_length) if self._content_length is not None else None
        return None

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeOpener:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.last_request: object | None = None

    def open(self, request: object) -> _FakeResponse:
        self.last_request = request
        return self._response


class TestFetch:
    def test_writes_payload_to_dest(self, tmp_path: Path) -> None:
        opener = _FakeOpener(_FakeResponse(b"hello-pack"))
        fetcher = HttpPackFetcher(opener=opener)  # type: ignore[arg-type]
        dest = tmp_path / "out.skillpack"
        path = fetcher.fetch("https://example.com/x.skillpack", dest)
        assert path == dest
        assert dest.read_bytes() == b"hello-pack"

    def test_rejects_non_http_urls(self, tmp_path: Path) -> None:
        fetcher = HttpPackFetcher(opener=_FakeOpener(_FakeResponse(b"")))  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="http"):
            fetcher.fetch("file:///etc/passwd", tmp_path / "x.skillpack")

    def test_enforces_size_cap_via_content_length(self, tmp_path: Path) -> None:
        big = _FakeResponse(b"", content_length=DEFAULT_MAX_BYTES + 1)
        fetcher = HttpPackFetcher(opener=_FakeOpener(big))  # type: ignore[arg-type]
        with pytest.raises(FetchTooLargeError):
            fetcher.fetch("https://example.com/big", tmp_path / "x.skillpack")

    def test_enforces_size_cap_during_streaming(self, tmp_path: Path) -> None:
        # Pretend Content-Length is missing and stream more than the cap.
        payload = b"x" * 200
        response = _FakeResponse(payload, content_length=None)
        fetcher = HttpPackFetcher(
            max_bytes=100, opener=_FakeOpener(response)  # type: ignore[arg-type]
        )
        with pytest.raises(FetchTooLargeError):
            fetcher.fetch("https://example.com/big", tmp_path / "x.skillpack")
        assert not (tmp_path / "x.skillpack").exists()


class TestFetchIndex:
    def test_decodes_index_payload(self) -> None:
        json_text = (
            '{"format_version": "1", "registry_name": "r", '
            '"base_url": "https://example.com", "updated_at": "t", "skills": []}'
        )
        opener = _FakeOpener(_FakeResponse(json_text.encode("utf-8")))
        fetcher = HttpPackFetcher(opener=opener)  # type: ignore[arg-type]
        index = fetcher.fetch_index("https://example.com/index.json")
        assert index.registry_name == "r"
        assert index.skills == ()
