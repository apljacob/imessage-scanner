"""Unit tests for the typedstream NSAttributedString decoder.

Fixtures are synthesized in-memory (see _make_blob below) so the test suite
contains no real iMessage data — safe to publish.
"""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))

import typedstream  # noqa: E402


# Apple typedstream prefix observed across all real attributedBody blobs:
#   \x04\x0bstreamtyped — magic
#   \x81\xe8\x03         — typedstream version
#   \x84\x01\x40         — class hierarchy framing
#   \x84\x84\x84\x12 NSAttributedString \x00
#   \x84\x84\x08 NSObject \x00
#   \x85\x92\x84\x84\x84\x08 NSString \x01\x94
#   \x84\x01\x2b         — value-start marker
#   <length><utf-8 text>
_PREFIX = (
    b"\x04\x0bstreamtyped"
    b"\x81\xe8\x03"
    b"\x84\x01\x40"
    b"\x84\x84\x84\x12NSAttributedString\x00"
    b"\x84\x84\x08NSObject\x00"
    b"\x85\x92\x84\x84\x84\x08NSString\x01\x94"
    b"\x84\x01\x2b"
)


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    if n < 0x10000:
        return b"\x82" + struct.pack(">H", n)
    return b"\x83" + struct.pack(">I", n)[1:]


def _make_blob(text: str) -> bytes:
    """Build a minimal valid typedstream NSAttributedString blob."""
    payload = text.encode("utf-8")
    return _PREFIX + _encode_length(len(payload)) + payload


def test_decode_returns_none_for_empty_blob():
    assert typedstream.decode(b"") is None


def test_decode_returns_none_for_garbage():
    assert typedstream.decode(b"\x00\x01\x02not a typedstream") is None


@pytest.mark.parametrize("text", [
    "hello world",
    "short",
    "Multi-line\ntext\nwith newlines",
    "Unicode: emoji \U0001F389 and curly quotes “like this”",
    "x" * 200,                       # exercises 1-byte length boundary
    "y" * 500,                       # exercises 2-byte length prefix
])
def test_decode_roundtrip(text):
    blob = _make_blob(text)
    assert typedstream.decode(blob) == text


def test_decode_handles_truncated_blob():
    # Cut a valid blob in half to ensure decoder fails gracefully, not crashes.
    blob = _make_blob("a normal message")
    assert typedstream.decode(blob[:len(blob) // 2]) is None
