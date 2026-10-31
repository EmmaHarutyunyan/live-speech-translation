"""Convert one conversation from a Claude data export (ZIP with conversations.json) to Markdown, unchanged.

Standard library only. The script reads the ZIP in memory (nothing is extracted), finds the conversation whose
title matches --title EXACTLY, and writes every message in its original order. Message content is copied as it
is: no summarising, no shortening, no re-wording. Content it does not recognise is NOT dropped: it is written as
raw JSON and listed in a report at the end, so nothing disappears silently.

Usage (from the project folder):
    .\\.venv\\Scripts\\python.exe scripts\\export_challenge_chat.py ^
        --zip chats\\export\\conversations-000.zip ^
        --title "Mathrix AI coding challenge setup" ^
        --output chats\\01-live-armenian-translation.md

Options:
    --uuid UUID     pick one conversation if several have the same title
    --force         overwrite --output if it already exists
"""

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

CONVERSATIONS_FILE = "conversations.json"

# Content block types this script knows how to lay out. Anything else is written as raw JSON and reported.
KNOWN_BLOCK_TYPES = {"text", "thinking", "tool_use", "tool_result", "voice_note", "token_budget"}
# Message fields that are written explicitly; other non-empty fields are written as raw JSON and reported.
KNOWN_MESSAGE_FIELDS = {"uuid", "sender", "created_at", "updated_at", "text", "content",
                        "attachments", "files", "index", "parent_message_uuid", "truncated", "stop_reason"}


class Report:
    """Collects everything that was not laid out in a known way (it is still written, as raw JSON)."""

    def __init__(self) -> None:
        self.unknown_block_types: Counter = Counter()
        self.unknown_message_fields: Counter = Counter()
        self.unusual_values: list[str] = []

    def print(self) -> None:
        if not (self.unknown_block_types or self.unknown_message_fields or self.unusual_values):
            print("report: every item was in a supported format.")
            return
        print("report: some items were in formats this script does not lay out specially.")
        print("        They are INCLUDED in the Markdown as raw JSON (nothing was skipped):")
        for name, n in sorted(self.unknown_block_types.items()):
            print(f"   content block type {name!r}: {n}x")
        for name, n in sorted(self.unknown_message_fields.items()):
            print(f"   message field {name!r}: {n}x")
        for note in self.unusual_values:
            print(f"   {note}")


def fence(body: str, info: str = "") -> str:
    """Code fence longer than any backtick run in the body, so the content can never break the Markdown."""
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{info}\n{body}\n{ticks}"


def as_text(value) -> str:
    """Strings unchanged; everything else as pretty JSON (non-ASCII kept, e.g. Armenian)."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def render_tool_result_content(content, report: Report, where: str) -> str:
    if isinstance(content, str):
        return fence(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(fence(item["text"]))
            else:
                kind = item.get("type") if isinstance(item, dict) else type(item).__name__
                report.unusual_values.append(f"{where}: tool result item of type {kind!r} written as raw JSON")
                parts.append(fence(as_text(item), "json"))
        return "\n\n".join(parts) if parts else "_(empty tool result)_"
    if content is None:
        return "_(empty tool result)_"
    report.unusual_values.append(f"{where}: tool result content of type {type(content).__name__} written as raw JSON")
    return fence(as_text(content), "json")


def render_block(block, report: Report, where: str) -> str:
    if not isinstance(block, dict):
        report.unusual_values.append(f"{where}: content item of type {type(block).__name__} written as raw JSON")
        return fence(as_text(block), "json")
    kind = block.get("type")
    if kind == "text":
        return as_text(block.get("text", ""))
    if kind == "thinking":
        return "**[thinking]**\n\n" + fence(as_text(block.get("thinking", "")))
    if kind == "tool_use":
        name = block.get("name", "?")
        return f"**[tool call: {name}]**\n\n" + fence(as_text(block.get("input", {})), "json")
    if kind == "tool_result":
        name = block.get("name")
        title = f"**[tool result{': ' + name if name else ''}{' — error' if block.get('is_error') else ''}]**"
        return title + "\n\n" + render_tool_result_content(block.get("content"), report, where)
    if kind == "voice_note":
        return "**[voice note]**\n\n" + fence(as_text(block.get("transcript") or block), "json"
                                                if not block.get("transcript") else "")
    if kind == "token_budget":
        return "**[token budget]** " + as_text({k: v for k, v in block.items() if k != "type"})
    report.unknown_block_types[str(kind)] += 1
    return f"**[unsupported content block: {kind}]**\n\n" + fence(as_text(block), "json")


def render_attachments(message: dict, report: Report, where: str) -> list[str]:
    parts = []
    for att in message.get("attachments") or []:
        if not isinstance(att, dict):
            report.unusual_values.append(f"{where}: attachment of type {type(att).__name__} written as raw JSON")
            parts.append("**[attachment]**\n\n" + fence(as_text(att), "json"))
            continue
        name = att.get("file_name") or att.get("name") or "(no name)"
        extra = {k: v for k, v in att.items() if k not in ("file_name", "name", "extracted_content")}
        text = f"**[attachment: {name}]**"
        if extra:
            text += "\n\n" + fence(as_text(extra), "json")
        if att.get("extracted_content") is not None:
            text += "\n\n" + fence(as_text(att["extracted_content"]))
        parts.append(text)
    for item in message.get("files") or []:
        name = item.get("file_name") if isinstance(item, dict) else None
        parts.append(f"**[file: {name}]**" if name else "**[file]**\n\n" + fence(as_text(item), "json"))
    return parts


def render_message(n: int, message: dict, report: Report) -> str:
    sender = message.get("sender", "?")
    created = message.get("created_at", "")
    where = f"message {n}"
    lines = [f"## {n}. {sender} — {created}"]

    content = message.get("content")
    if isinstance(content, list) and content:
        lines += [render_block(b, report, where) for b in content]
        # Some exports also keep a flat "text" copy; write it only if it holds text not found in the blocks.
        flat = message.get("text")
        joined = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(flat, str) and flat.strip() and flat.strip() not in joined:
            lines.append("**[message text field]**\n\n" + flat)
    elif isinstance(message.get("text"), str):
        lines.append(message["text"])
    elif content not in (None, []):
        report.unusual_values.append(f"{where}: content of type {type(content).__name__} written as raw JSON")
        lines.append(fence(as_text(content), "json"))
    else:
        lines.append("_(no content in export)_")

    lines += render_attachments(message, report, where)

    for key, value in message.items():
        if key in KNOWN_MESSAGE_FIELDS or value in (None, "", [], {}):
            continue
        report.unknown_message_fields[key] += 1
        lines.append(f"**[field: {key}]**\n\n" + fence(as_text(value), "json"))
    return "\n\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zip", required=True, type=Path, help="export ZIP that contains conversations.json")
    parser.add_argument("--title", required=True, help="exact conversation title")
    parser.add_argument("--output", required=True, type=Path, help="Markdown file to write")
    parser.add_argument("--uuid", help="conversation uuid, if several have the same title")
    parser.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"ERROR: {args.output} already exists (use --force to overwrite).", file=sys.stderr)
        return 1
    with zipfile.ZipFile(args.zip) as archive:
        if CONVERSATIONS_FILE not in archive.namelist():
            print(f"ERROR: {CONVERSATIONS_FILE} not found in {args.zip}.", file=sys.stderr)
            return 1
        conversations = json.loads(archive.read(CONVERSATIONS_FILE).decode("utf-8"))
    if not isinstance(conversations, list):
        print(f"ERROR: expected a list of conversations, got {type(conversations).__name__}.", file=sys.stderr)
        return 1

    # Only the count of other conversations is printed, never their titles or content.
    matches = [c for c in conversations if isinstance(c, dict) and c.get("name") == args.title]
    if args.uuid:
        matches = [c for c in matches if c.get("uuid") == args.uuid]
    if len(matches) != 1:
        print(f"ERROR: {len(matches)} conversations match this title"
              f"{' and uuid' if args.uuid else ''} (export has {len(conversations)} in total). "
              f"Need exactly 1{'; use --uuid' if len(matches) > 1 else ''}.", file=sys.stderr)
        return 1
    conv = matches[0]
    messages = conv.get("chat_messages")
    if not isinstance(messages, list):
        print("ERROR: conversation has no chat_messages list.", file=sys.stderr)
        return 1

    report = Report()
    header = [
        f"# {conv.get('name')}",
        "",
        "Complete, unedited transcript converted from the official Claude data export "
        f"(`{args.zip.name}` → `{CONVERSATIONS_FILE}`) by `scripts/export_challenge_chat.py`.",
        "Messages are in the export's original order; content is copied without changes.",
        "",
        f"- Conversation uuid: `{conv.get('uuid')}`",
        f"- Created: {conv.get('created_at')}",
        f"- Last updated: {conv.get('updated_at')}",
        f"- Messages: {len(messages)}",
    ]
    if conv.get("summary"):
        header += ["", "**[conversation summary field from the export]**", "", fence(as_text(conv["summary"]))]
    body = [render_message(n, m if isinstance(m, dict) else {"content": m}, report)
            for n, m in enumerate(messages, start=1)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(header) + "\n\n---\n\n" + "\n\n---\n\n".join(body) + "\n",
                           encoding="utf-8", newline="\n")

    senders = Counter(m.get("sender", "?") for m in messages if isinstance(m, dict))
    times = [m.get("created_at") for m in messages if isinstance(m, dict) and m.get("created_at")]
    print(f"wrote {args.output} ({args.output.stat().st_size:,} bytes)")
    print(f"messages: {len(messages)} written of {len(messages)} in the export  ({dict(senders)})")
    print(f"first message: {min(times) if times else '?'}   last message: {max(times) if times else '?'}")
    report.print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
