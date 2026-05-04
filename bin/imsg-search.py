#!/usr/bin/env python3
"""Search ~/Library/Messages/chat.db with structured filters; emit JSON or text.

Invoked by Claude after the /imsg-scan slash command parses the user's
natural-language query into structured args.
"""
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
import typedstream  # noqa: E402

DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"
APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970-01-01 and 2001-01-01


def parse_relative_date(s: str) -> datetime:
    """Accept '7d', '3m', '1y', or ISO 8601. Returns a UTC datetime."""
    s = s.strip()
    m = re.fullmatch(r"(\d+)([dmy])", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"d": n, "m": n * 30, "y": n * 365}[unit]
        return datetime.now(timezone.utc) - timedelta(days=days)
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError as e:
        raise ValueError(
            f"Could not parse date {s!r}. Use '7d', '3m', '1y', or ISO 8601 (2026-01-01)."
        ) from e


def datetime_to_apple_ns(dt: datetime) -> int:
    return int((dt.timestamp() - APPLE_EPOCH_OFFSET) * 1_000_000_000)


def apple_ns_to_iso(apple_ns: int) -> str:
    unix_seconds = apple_ns / 1_000_000_000 + APPLE_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()


def build_query(args) -> Tuple[str, List]:
    where = []
    params: List = []

    if args.from_:
        where.append("h.id = ?")
        params.append(args.from_)
    if args.to:
        where.append("(m.is_from_me = 1 AND h.id = ?)")
        params.append(args.to)
    if args.since:
        where.append("m.date >= ?")
        params.append(datetime_to_apple_ns(parse_relative_date(args.since)))
    if args.until:
        where.append("m.date <= ?")
        params.append(datetime_to_apple_ns(parse_relative_date(args.until)))
    if args.has_attachment:
        where.append(
            "EXISTS (SELECT 1 FROM message_attachment_join maj WHERE maj.message_id = m.ROWID)"
        )
    if args.chat:
        where.append("c.display_name LIKE ?")
        params.append(f"%{args.chat}%")

    where_sql = " AND ".join(where) if where else "1=1"

    sql = f"""
        SELECT
            m.ROWID,
            m.date,
            m.text,
            m.attributedBody,
            m.is_from_me,
            h.id AS handle,
            c.display_name AS chat_name,
            c.style AS chat_style
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.ROWID
        WHERE {where_sql}
        ORDER BY m.date DESC
        LIMIT ?
    """
    params.append(args.limit * 3 if args.keyword else args.limit)
    return sql, params


def fetch_results(args) -> dict:
    if not DB_PATH.exists():
        return {"results": [], "_meta": {"error": f"chat.db not found at {DB_PATH}"}}

    keyword_re = None
    if args.keyword:
        try:
            keyword_re = re.compile(args.keyword, re.IGNORECASE)
        except re.error as e:
            return {"results": [], "_meta": {"error": f"Invalid keyword regex: {e}"}}

    uri = f"file:{DB_PATH}?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as e:
        return {"results": [], "_meta": {
            "error": (
                f"Could not open chat.db: {e}. Grant Full Disk Access to your "
                "terminal in System Settings > Privacy & Security."
            )
        }}

    try:
        sql, params = build_query(args)
    except ValueError as e:
        return {"results": [], "_meta": {"error": str(e)}}
    rows = conn.execute(sql, params).fetchall()
    results = []
    decode_failures = 0
    total_seen = 0

    for rowid, date, text, attributed_body, is_from_me, handle, chat_name, chat_style in rows:
        total_seen += 1
        msg_text = text
        if not msg_text and attributed_body:
            decoded = typedstream.decode(attributed_body)
            if decoded is None:
                decode_failures += 1
                continue
            msg_text = decoded
        if not msg_text:
            continue
        if keyword_re and not keyword_re.search(msg_text):
            continue

        results.append({
            "rowid": rowid,
            "date": apple_ns_to_iso(date),
            "from_handle": handle,
            "from_name": None,  # filled by Claude using alias map
            "is_from_me": bool(is_from_me),
            "chat": chat_name or ("group" if chat_style == 43 else "1:1"),
            "text": msg_text,
        })
        if len(results) >= args.limit:
            break

    return {
        "results": results,
        "_meta": {
            "total_matched": len(results),
            "returned": len(results),
            "truncated": len(results) >= args.limit and total_seen >= args.limit * 3,
            "decode_failures": decode_failures,
            "scanned": total_seen,
        },
    }


def format_text(payload: dict) -> str:
    if "error" in payload.get("_meta", {}):
        return f"ERROR: {payload['_meta']['error']}"
    lines = [f"Found {len(payload['results'])} message(s):", ""]
    for r in payload["results"]:
        direction = "->" if r["is_from_me"] else "<-"
        who = r["from_handle"] or "you"
        lines.append(f"[{r['date']}] {direction} {who} ({r['chat']})")
        lines.append(f"    {r['text']}")
        lines.append("")
    if payload["_meta"].get("decode_failures"):
        lines.append(f"({payload['_meta']['decode_failures']} message(s) could not be decoded)")
    if payload["_meta"].get("truncated"):
        lines.append("(Result truncated -- narrow the query for more.)")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Search the local Messages chat.db.")
    p.add_argument("--from", dest="from_", help="Sender handle (phone or email)")
    p.add_argument("--to", help="Recipient handle (for outbound messages you sent)")
    p.add_argument("--keyword", help="Regex to match against message text (case-insensitive)")
    p.add_argument("--since", help="Earliest date (e.g. '7d', '3m', '2026-01-01')")
    p.add_argument("--until", help="Latest date (same formats as --since)")
    p.add_argument("--chat", help="Filter to chats whose display name contains this substring")
    p.add_argument("--has-attachment", action="store_true", help="Only messages with attachments")
    p.add_argument("--limit", type=int, default=100, help="Max results (default 100)")
    p.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    args = p.parse_args()

    payload = fetch_results(args)
    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        print(format_text(payload))


if __name__ == "__main__":
    main()
