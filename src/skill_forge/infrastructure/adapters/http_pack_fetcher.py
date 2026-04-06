"""Download skill packs over HTTP(S).

Uses the standard library's ``urllib`` so we don't pull in ``requests``
just for two GETs. Honors a ``GITHUB_TOKEN`` env var so private repos
work without configuration files.

The fetcher caps download size to defend against accidental or hostile
downloads of huge files. The default cap (50 MB) is far larger than any
reasonable skill bundle but small enough to refuse a runaway response.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path

from skill_forge.domain.model import RegistryIndex
from skill_forge.domain.ports import PackFetcher
from skill_forge.infrastructure.adapters.registry_index_codec import (
    RegistryIndexCodec,
)

DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class FetchTooLargeError(RuntimeError):
    """Raised when a download exceeds the configured size cap."""


class HttpPackFetcher(PackFetcher):
    """Fetch ``.skillpack`` files and ``index.json`` over HTTP(S)."""

    def __init__(
        self,
        max_bytes: int = DEFAULT_MAX_BYTES,
        codec: RegistryIndexCodec | None = None,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._codec = codec or RegistryIndexCodec()
        self._opener = opener or urllib.request.build_opener()

    # ------------------------------------------------------------------ public

    def fetch(self, url: str, dest: Path) -> Path:
        _require_http(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        request = self._build_request(url)
        try:
            with self._opener.open(request) as response:
                self._enforce_content_length(response)
                written = 0
                with dest.open("wb") as out:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > self._max_bytes:
                            out.close()
                            dest.unlink(missing_ok=True)
                            raise FetchTooLargeError(
                                f"Download exceeded {self._max_bytes} bytes: {url}"
                            )
                        out.write(chunk)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} fetching {url}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to fetch {url}: {e.reason}") from e
        return dest

    def fetch_index(self, url: str) -> RegistryIndex:
        _require_http(url)
        request = self._build_request(url)
        try:
            with self._opener.open(request) as response:
                self._enforce_content_length(response)
                payload = response.read(self._max_bytes + 1)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} fetching index {url}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to fetch index {url}: {e.reason}") from e
        if len(payload) > self._max_bytes:
            raise FetchTooLargeError(f"Index exceeded {self._max_bytes} bytes: {url}")
        return self._codec.decode(payload.decode("utf-8"))

    # ----------------------------------------------------------------- helpers

    def _build_request(self, url: str) -> urllib.request.Request:
        headers = {"User-Agent": "skill-forge"}
        token = os.environ.get("GITHUB_TOKEN")
        if token and "githubusercontent.com" in url:
            headers["Authorization"] = f"token {token}"
        return urllib.request.Request(url, headers=headers)

    def _enforce_content_length(self, response: object) -> None:
        # response is a urllib HTTPResponse but typed loosely so the opener
        # can be swapped out in tests.
        getheader = getattr(response, "getheader", None)
        if getheader is None:
            return
        length = getheader("Content-Length")
        if length is None:
            return
        try:
            value = int(length)
        except ValueError:
            return
        if value > self._max_bytes:
            raise FetchTooLargeError(
                f"Server reported {value} bytes, exceeds cap {self._max_bytes}"
            )


def _require_http(url: str) -> None:
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError(f"Only http(s) URLs are supported, got: {url}")
