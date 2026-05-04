---
description: Search the local iMessage history with a natural-language query
argument-hint: <natural language query>
allowed-tools: Bash, Read, Write, Skill
---

# /imsg-scan

The user wants to search their local iMessage history. Their query (natural language) is in `$ARGUMENTS`.

## Step 1: Classify the query

Pick one mode:

- **literal** — keyword/handle/date filter only. Examples: "messages from my landlord about the lease repair", "anything mentioning the Tokyo trip last month", "Alex's messages with links to that listing". Default mode.
- **intent** — needs semantic judgment over results. Examples: "find every commitment I made this month", "unanswered questions from clients in the last 2 weeks", "find anything that sounds like a deadline I haven't hit yet".
- **recall** — pure date/handle filter, no keyword. Examples: "what did anyone send me this morning", "show my last 20 messages with my mom", "show my last 5 messages".

## Step 2: Extract structured parameters

From the query, extract:
- `--from <name|handle>` — sender (resolve name via alias map; see Step 3)
- `--to <name|handle>` — recipient (only for outbound queries)
- `--keyword <regex>` — text to match (literal/intent modes)
- `--since <relative>` — `1d`, `7d`, `30d`, `1y`, or absolute ISO date
- `--until <relative>` — same formats
- `--chat <name>` — group chat filter
- `--has-attachment` — flag
- `--limit <N>` — default 100

Defaults if not specified:
- `--limit 100`
- `--since 90d` (lift this if user says "all time", "ever", "all my history")

## Step 3: Resolve names to handles

If the query references a person by name (e.g. "Alex"):

1. Run `Bash: python3 $CLAUDE_PLUGIN_ROOT/bin/imsg-aliases.py --lookup "Alex"`
2. If `matches` is non-empty, use those handles for `--from`/`--to`.
3. If empty AND `~/.imsg-scan/aliases.json` does not exist:
   - Build it: call the `apple-mcp` contacts tool to fetch the address book.
   - Format as `{"Name": ["phone or email", ...]}` and pipe to `python3 $CLAUDE_PLUGIN_ROOT/bin/imsg-aliases.py --write-from-stdin`.
   - Re-run the lookup.
4. If still empty: ask the user "I don't have a handle for <name>. What's their phone number or email?" Then call `imsg-aliases.py --add <name> <handle>` with their answer and proceed.
5. If the lookup returns multiple matches, ask the user to disambiguate before proceeding.

If `apple-mcp` is not available, skip the auto-build and ask the user for the handle directly.

## Step 4: Run the search

```
Bash: python3 $CLAUDE_PLUGIN_ROOT/bin/imsg-search.py [args from step 2] --format json
```

Parse the JSON output. Shape: `{"results": [...], "_meta": {...}}`.

## Step 5: Apply intent filter (intent mode only)

If mode is `intent`:
1. Use the Skill tool to invoke `imessage-scanner:intent-filter`, passing the JSON results and the user's intent description.
2. The skill returns a filtered subset.

## Step 6: Format and present

For each result, display:
- Local time (convert from ISO)
- Direction (`→ from you` / `← from <name>`), resolving handles back to names via the alias map
- Chat context (1:1 vs group name)
- Message text (truncate at ~200 chars per message; show full on user request)

If `_meta.truncated` is true: "Showing N — narrow the query for more."
If `_meta.decode_failures > 0`: mention how many messages couldn't be decoded.
If results are empty: say "No matches" — never fabricate.

## Examples

User: `/imsg-scan show me my last 5 messages`
- mode: recall
- args: `--limit 5`

User: `/imsg-scan messages from Alex about the lease repair in the last 90 days`
- mode: literal
- resolve "Alex" → +15555550100
- args: `--from "+15555550100" --keyword "lease|repair" --since 90d`

User: `/imsg-scan find every commitment I made in the last 30 days`
- mode: intent
- args: `--since 30d --limit 200`
- after JSON returned: invoke intent-filter skill with intent="commitments I made"
