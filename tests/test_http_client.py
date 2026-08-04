"""Test cases for Bayrol HTTP client helpers."""

import pytest

from custom_components.bayrol_cloud.client.http_client import _read_html_response


class FakeResponse:
    """Minimal response object for testing HTML decoding."""

    def __init__(
        self,
        body: bytes,
        charset: str | None = None,
        detected_encoding: str | Exception | None = None,
    ) -> None:
        self._body = body
        self.charset = charset
        self._detected_encoding = detected_encoding

    async def read(self) -> bytes:
        """Return raw response body bytes."""
        return self._body

    def get_encoding(self) -> str:
        """Return aiohttp-style detected response encoding."""
        if isinstance(self._detected_encoding, Exception):
            raise self._detected_encoding
        if self._detected_encoding:
            return self._detected_encoding
        if self.charset:
            return self.charset
        return "utf-8"


@pytest.mark.asyncio
async def test_read_html_response_decodes_declared_utf8() -> None:
    """Decode valid UTF-8 HTML using the declared charset."""
    expected = "<html>gr\u00f6\u00dfer</html>"
    response = FakeResponse(expected.encode(), charset="UTF-8")

    assert await _read_html_response(response) == expected


@pytest.mark.asyncio
async def test_read_html_response_decodes_declared_iso_8859_1() -> None:
    """Decode Latin-1 HTML when the response declares Latin-1."""
    response = FakeResponse(b"<html>gr\xf6\xdfer</html>", charset="iso-8859-1")

    assert await _read_html_response(response) == "<html>gr\u00f6\u00dfer</html>"


@pytest.mark.asyncio
async def test_read_html_response_falls_back_from_invalid_utf8() -> None:
    """Fall back when the response declares UTF-8 but contains legacy bytes."""
    response = FakeResponse(b"<html>gr\xf6\xdfer</html>", charset="UTF-8")

    assert await _read_html_response(response) == "<html>gr\u00f6\u00dfer</html>"


@pytest.mark.asyncio
async def test_read_html_response_falls_back_when_charset_missing() -> None:
    """Use fallback decoding when no usable charset is available."""
    response = FakeResponse(
        b"<html>gr\xf6\xdfer</html>",
        charset=None,
        detected_encoding=RuntimeError("encoding unavailable"),
    )

    assert await _read_html_response(response) == "<html>gr\u00f6\u00dfer</html>"
