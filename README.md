# iMessage Scanner

A [Claude Code](https://claude.com/claude-code) plugin that lets you search your local iMessage history with natural-language queries via `/imsg-scan`.

Reads `~/Library/Messages/chat.db` directly (read-only), decodes Apple's `attributedBody` typedstream blobs (which hold ~82% of modern message content), and returns matched messages. No cloud, no API calls — your messages never leave your machine.

## What it does

```text
/imsg-scan show me my last 5 messages
/imsg-scan find every commitment I made in the last 30 days
/imsg-scan unanswered questions from clients in the last 2 weeks
/imsg-scan messages with attachments from my accountant this year
/imsg-scan anything Alex sent me about the apartment
```

Claude classifies your query into one of three modes:
- **literal** — keyword + handle + date filter (pure SQL)
- **intent** — semantic filter ("unanswered questions", "commitments I made", "deadlines") via a bundled skill
- **recall** — date/handle filter only ("show my last N messages")

## Install

```bash
claude plugin marketplace add apljacob/imessage-scanner
claude plugin install imessage-scanner@imessage-scanner
```

Then open a Claude Code session and run `/imsg-scan show me my last 5 messages`.

## Prerequisites

1. **macOS** with iMessage configured (your local `~/Library/Messages/chat.db` is the source of truth)
2. **Full Disk Access** for the terminal you run Claude Code from
   - System Settings → Privacy & Security → Full Disk Access → add Terminal (or VS Code, Warp, iTerm2, whatever you use)
   - Restart your terminal after granting
3. **Python 3.9+** (uses stdlib only — no `pip install` needed)
4. **Optional: [`apple-mcp`](https://github.com/dhravya/apple-mcp)** — used on first run to auto-build the contact alias map. Without it you can hand-add aliases with `bin/imsg-aliases.py --add <name> <handle>`.

## How it works

| Component | Purpose |
|---|---|
| `commands/imsg-scan.md` | Slash command spec — instructions for Claude on how to translate natural language into structured args |
| `bin/imsg-search.py` | SQL executor: opens `chat.db` read-only, runs a parameterized query, decodes attributedBody, returns JSON |
| `bin/typedstream.py` | Pure-Python decoder for Apple's NSAttributedString typedstream binary format |
| `bin/imsg-aliases.py` | Manages `~/.imsg-scan/aliases.json` (name → handle map), normalizes phone numbers to E.164 |
| `skills/intent-filter/SKILL.md` | Invoked by Claude when the query needs semantic judgment |

## Acceptance test queries

These five queries verify the plugin end-to-end after installing:

| # | Query | Verifies |
|---|---|---|
| 1 | `/imsg-scan show me my last 5 messages` | Recall mode, basic SQL + decode |
| 2 | `/imsg-scan messages from <name> mentioning <topic> in the last 30 days` | Literal mode, alias resolution, keyword filter |
| 3 | `/imsg-scan find unanswered questions to me from this week` | Intent mode, intent-filter skill |
| 4 | `/imsg-scan messages with attachments from this month` | `--has-attachment` flag |
| 5 | `/imsg-scan anything mentioning "<keyword>" ever` | "all time" handling, broad scan |

## Direct CLI usage

The Python scripts work standalone if you want to skip Claude:

```bash
# Search directly
python3 bin/imsg-search.py --limit 5 --format text
python3 bin/imsg-search.py --keyword "Verizon" --since 7d --format json

# Manage the alias map
echo '{"Mom": ["+15551234567"]}' | python3 bin/imsg-aliases.py --write-from-stdin
python3 bin/imsg-aliases.py --lookup Mom
python3 bin/imsg-aliases.py --add Dad +15559876543

# Run the test suite
python3 -m pytest tests/ -v
```

## Privacy

- Read-only. The chat.db is opened with `?mode=ro&immutable=1` — even SQLite-level writes are blocked.
- No network calls. Nothing is sent anywhere.
- Alias map is stored at `~/.imsg-scan/aliases.json` on your machine only.
- Plugin permissions are scoped narrowly: only the two Python scripts can be run via Bash, only `chat.db` can be read, only the alias file can be read/written.

## Troubleshooting

| Error | Fix |
|---|---|
| `unable to open database file` | Grant Full Disk Access to your terminal/VS Code, then restart Claude. |
| Many `decode_failures` in `_meta` | Capture the failing blob (`bin/imsg-search.py --limit 1 --format json`), open an issue with the hex dump. The decoder handles ~99% of real messages but some edge cases (notably reactions with non-standard length encoding) currently fall through. |
| `apple-mcp` not available, names won't resolve | Hand-add: `python3 bin/imsg-aliases.py --add Mom +15551234567` |
| Plugin not appearing in `/help` | Run `claude plugin list` to confirm install; restart Claude Code. |

## Out of scope (v0.1.0)

Deliberate v1 limitations — open to PRs:

- Sending messages (use [`apple-mcp`](https://github.com/dhravya/apple-mcp) for that)
- Reactions/tapbacks (separate `associated_message` rows)
- Real-time monitoring / new-message alerts
- FTS5 pre-index (only needed if scan latency on large corpora becomes painful)
- Cross-device iCloud sync (only reads local `chat.db`)
- Attachment file download (returns metadata only — file path, MIME type)

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow. Run `python3 -m pytest tests/ -v` before submitting.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Built with [Claude Code](https://claude.com/claude-code) and the official [`plugin-dev`](https://github.com/anthropics/claude-plugins-official) workflow.
- Apple typedstream format documented by the [`imessage-exporter`](https://github.com/ReagentX/imessage-exporter) project.
