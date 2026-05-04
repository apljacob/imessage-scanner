---
name: intent-filter
description: This skill should be used when filtering a JSON list of iMessage search results (output of bin/imsg-search.py) by a semantic criterion such as unanswered questions, commitments made, deadlines, or messages needing a response. Invoked by the /imsg-scan planner in intent mode; not triggered directly by user phrasing. Returns the filtered subset with a one-line match rationale per kept message.
---

# Intent Filter

Filter a JSON list of iMessage search results by a semantic intent. The input is the output of `bin/imsg-search.py --format json` plus an intent string supplied by the caller.

## Inputs

The caller (the `/imsg-scan` planner) provides two things in the prompt:

1. **JSON results blob** — the full payload from `imsg-search.py`, shape `{"results": [...], "_meta": {...}}`. Each result has `rowid`, `date`, `from_handle`, `from_name`, `is_from_me`, `chat`, `text`.
2. **Intent string** — a short phrase like `"unanswered questions to me"` or `"commitments I made"`.

## Process

### Step 1: Token-cap check

If `len(results) > 500`, return early:

```json
{"error": "too_many_messages", "scanned": <N>}
```

The planner will ask the user to narrow the query.

### Step 2: Apply the intent filter

For each message in `results`, decide if it matches the intent. Be strict — exclude on uncertainty.

- **"unanswered questions to me"** — keep messages where `is_from_me == false` AND the text contains a question (ends in `?` or starts with question word) AND no later (more recent) row in the same chat has `is_from_me == true`. Group by the `chat` field; treat identical chat strings as the same conversation. Note that `chat` is a human-readable label, not a stable ID, so collisions are possible — accept this limitation.
  - Keep: `"can you send the signed lease back today?"` from Alex with no later outgoing message in that chat.
  - Reject: `"hey"` (no question), or `"got a sec?"` if you sent any message in that chat afterward.

- **"commitments I made"** — keep messages where `is_from_me == true` that promise an action ("I'll send it", "will do", "on it", "let me get back to you").
  - Keep: `"I'll send the invoice tonight"`.
  - Reject: `"I might"`, `"maybe later"`, `"thinking about it"` — not a firm commitment.

- **"deadlines"** — keep messages from anyone that mention a date or time implying an action ("by Friday", "before noon", "this weekend"). Include both inbound and outbound. Don't filter by whether the deadline has passed — surface them all.
  - Keep: `"need this by EOD Thursday"`.
  - Reject: `"on Friday we went hiking"` (past-tense, no action implied).

For other intents the caller provides, infer reasonable matching rules and apply the same strictness bar.

### Step 3: Compute counts and emit

Set `scanned = len(input.results)`, `removed = scanned - len(filtered)`. Preserve input order (which is date descending). If the input order looks shuffled, sort defensively by `date` descending before emitting.

## Constraints

- **Never fabricate.** Don't add messages that weren't in the input. Don't paraphrase the `text` field.
- **One match_reason per kept message.** Single short sentence explaining why.

## Output format

```json
{
  "filtered": [
    {
      "rowid": 1,
      "date": "2026-05-01T10:00:00+00:00",
      "from_handle": "+1...",
      "from_name": "Alex",
      "is_from_me": false,
      "chat": "1:1 with Alex",
      "text": "can you send the signed lease back today?",
      "match_reason": "Direct question with no reply from you in this chat."
    }
  ],
  "removed": 23,
  "scanned": 45
}
```
