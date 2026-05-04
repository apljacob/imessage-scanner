# Changelog

## v0.1.0 — 2026-05-03

Initial public release.

### Added
- `/imsg-scan <natural language>` slash command for searching local iMessage history
- Pure-Python typedstream decoder (`bin/typedstream.py`) for Apple's `attributedBody` NSAttributedString blobs (~99% real-world success rate)
- SQL executor (`bin/imsg-search.py`) with `--from`, `--to`, `--keyword`, `--since`, `--until`, `--chat`, `--has-attachment`, `--limit`, `--format` flags
- Alias map manager (`bin/imsg-aliases.py`) with E.164 phone-number normalization
- `intent-filter` skill for semantic queries ("unanswered questions", "commitments", "deadlines")
- Read-only access via SQLite `?mode=ro&immutable=1` URI — bypasses Messages-app lock and prevents writes
- Test suite with synthetic typedstream fixtures (no real message data committed)

### Known limitations
- Reaction messages with non-standard `0x81` + 16-bit length encoding return `None` from the decoder (logged in `_meta.decode_failures`, never crashes)
- Contact resolution requires either `apple-mcp` (auto-build on first run) or manual `imsg-aliases.py --add` entries
- macOS only — reads `~/Library/Messages/chat.db` directly
