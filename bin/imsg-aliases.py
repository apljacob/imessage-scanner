#!/usr/bin/env python3
"""Manage the iMessage scanner alias map at ~/.imsg-scan/aliases.json.

Usage:
  imsg-aliases.py --lookup <name>            # print matching handle(s) as JSON
  imsg-aliases.py --add <name> <handle>      # append handle under name
  imsg-aliases.py --write-from-stdin         # overwrite map from stdin JSON
  imsg-aliases.py --list                     # print full map
"""
import argparse
import json
import re
import sys
from pathlib import Path

ALIAS_PATH = Path.home() / ".imsg-scan" / "aliases.json"


def normalize_handle(h: str) -> str:
    """Normalize phone numbers to E.164 (digits only with leading +).
    Emails are lowercased and returned as-is."""
    h = h.strip()
    if "@" in h:
        return h.lower()
    digits = re.sub(r"\D", "", h)
    if len(digits) == 10:
        digits = "1" + digits  # default to US country code
    return "+" + digits


def load_map() -> dict:
    if not ALIAS_PATH.exists():
        return {}
    return json.loads(ALIAS_PATH.read_text())


def save_map(m: dict):
    ALIAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALIAS_PATH.write_text(json.dumps(m, indent=2))


def cmd_lookup(name: str):
    m = load_map()
    name_lower = name.lower()
    matches = []
    for k, handles in m.items():
        if k.lower() == name_lower or name_lower in k.lower():
            matches.extend((k, h) for h in handles)
    print(json.dumps({
        "query": name,
        "matches": [{"name": n, "handle": h} for n, h in matches],
    }, indent=2))


def cmd_add(name: str, handle: str):
    m = load_map()
    norm = normalize_handle(handle)
    m.setdefault(name, [])
    if norm not in m[name]:
        m[name].append(norm)
    save_map(m)
    print(json.dumps({"added": {name: norm}, "total_names": len(m)}))


def cmd_write_from_stdin():
    """Overwrite the alias map with JSON read from stdin."""
    raw = json.loads(sys.stdin.read())
    if not isinstance(raw, dict):
        print(json.dumps({"error": "expected JSON object {name: [handles]}"}), file=sys.stderr)
        sys.exit(1)
    cleaned = {
        name: [
            normalize_handle(h)
            for h in (handles if isinstance(handles, list) else [handles])
        ]
        for name, handles in raw.items()
    }
    save_map(cleaned)
    print(json.dumps({"wrote": str(ALIAS_PATH), "names": len(cleaned)}))


def cmd_list():
    print(json.dumps(load_map(), indent=2))


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--lookup", metavar="NAME")
    g.add_argument("--add", nargs=2, metavar=("NAME", "HANDLE"))
    g.add_argument("--write-from-stdin", action="store_true")
    g.add_argument("--list", action="store_true")
    args = p.parse_args()

    if args.lookup:
        cmd_lookup(args.lookup)
    elif args.add:
        cmd_add(args.add[0], args.add[1])
    elif args.write_from_stdin:
        cmd_write_from_stdin()
    elif args.list:
        cmd_list()


if __name__ == "__main__":
    main()
