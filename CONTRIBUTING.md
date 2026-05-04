# Contributing

Thanks for your interest. PRs and issues are welcome.

## Setup

```bash
git clone https://github.com/apljacob/imessage-scanner.git
cd imessage-scanner
python3 -m pytest tests/ -v
```

The test suite uses synthetic typedstream blobs — no real iMessage data is required to run tests.

## Workflow

1. Open an issue first for non-trivial changes — keeps us aligned before you spend time.
2. Fork → branch → PR.
3. Run `python3 -m pytest tests/ -v` and confirm all tests pass.
4. If you change the typedstream decoder, add a synthetic test case for the new format you're handling.
5. Keep PRs focused — one feature or fix per PR.

## What we're looking for

- **Decoder edge cases** — Reaction messages with the `0x81` length prefix currently fall through. Patches welcome with synthetic test fixtures.
- **Cross-platform support** — Currently macOS-only. Linux/Windows ports would need to bring their own data source since `chat.db` is Apple-specific.
- **FTS5 indexer** — Optional pre-index over decoded text for sub-second search on million-message corpora. Specced in the design doc but not built.
- **More intent types** for the `intent-filter` skill — "messages I haven't replied to in over a week", "all promises made to me by X", etc.

## What we're NOT looking for

- Sending messages — use [`apple-mcp`](https://github.com/dhravya/apple-mcp) for that. This plugin is read-only by design.
- Network calls — keep the privacy story intact.
- Third-party Python dependencies — stdlib only. The plugin must work after `claude plugin install` with no `pip` step.

## Code style

- Python 3.9+ compatible (use `from typing import Optional` not `str | None`)
- Stdlib only — no `requirements.txt`, no `pip install`
- Tests for any new decoder logic
- Match the existing style: argparse for CLIs, JSON for I/O between scripts
