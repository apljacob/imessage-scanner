"""Pure-Python decoder for Apple's typedstream NSAttributedString blobs.

iMessage stores message content in the `attributedBody` column as a binary
typedstream serialization of an NSAttributedString. The text payload is the
NSString embedded inside. This decoder extracts the UTF-8 string and ignores
all attributes (formatting, links, etc.).
"""
import struct
from typing import Optional, Tuple


# Sequence that marks the NSString instance value (vs the class declaration).
# Observed in all real fixtures as: <class-version-byte 0x94|0x95> 0x84 0x01 0x2b <length> <utf8 text>
_VALUE_START = b"\x84\x01\x2b"


def decode(blob: bytes) -> Optional[str]:
    """Return the message text from a typedstream attributedBody blob, or None."""
    if not blob or len(blob) < 16:
        return None
    if not blob.startswith(b"\x04\x0bstreamtyped"):
        return None

    # Locate any NSString class marker. The class hierarchy may declare
    # NSMutableString and NSString as nested type info; the actual VALUE
    # comes later, marked by 0x84 0x01 0x2b followed by a length prefix.
    marker_idx = blob.find(b"NSString")
    if marker_idx == -1:
        return None

    # Scan forward from the marker for the value-start sequence.
    value_idx = blob.find(_VALUE_START, marker_idx)
    if value_idx == -1:
        return None

    cursor = value_idx + len(_VALUE_START)
    length, cursor = _read_length(blob, cursor)
    if length is None or cursor + length > len(blob):
        return None

    text_bytes = blob[cursor:cursor + length]
    try:
        return text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return text_bytes.decode("utf-16-be")
        except UnicodeDecodeError:
            return None


def _read_length(blob: bytes, cursor: int) -> Tuple[Optional[int], int]:
    if cursor >= len(blob):
        return None, cursor
    b = blob[cursor]
    if b < 0x80:
        return b, cursor + 1
    if b == 0x81:
        if cursor + 1 >= len(blob):
            return None, cursor
        return blob[cursor + 1], cursor + 2
    if b == 0x82:
        if cursor + 2 >= len(blob):
            return None, cursor
        (length,) = struct.unpack(">H", blob[cursor + 1:cursor + 3])
        return length, cursor + 3
    if b == 0x83:
        if cursor + 3 >= len(blob):
            return None, cursor
        (length,) = struct.unpack(">I", b"\x00" + blob[cursor + 1:cursor + 4])
        return length, cursor + 4
    if b == 0x84:
        if cursor + 4 >= len(blob):
            return None, cursor
        (length,) = struct.unpack(">I", blob[cursor + 1:cursor + 5])
        return length, cursor + 5
    return None, cursor


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            print(decode(f.read()))
