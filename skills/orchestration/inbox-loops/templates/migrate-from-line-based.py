#!/usr/bin/env python3
"""Migrate legacy line-based inbox files to file-per-task layout.

Reads <inbox-dir>/inbox-prs.md, inbox-tickets.md, inbox-vulns.md and writes
one markdown file per task to <inbox-dir>/tasks/<kind>-<key>.md with YAML
frontmatter. Vuln entries get ## Taint and ## Repro body sections built from
the indented "- taint:" / "- repro:" continuation lines.

Idempotent: existing output files are left untouched.

Usage:
    python3 migrate-from-line-based.py <inbox-dir>
"""

import re
import sys
from datetime import date
from pathlib import Path

# Kind whitelist. Composite kinds first so longest-prefix match works when
# parsing a kind off a filename (not used by this script directly, but kept
# here as the canonical list).
KIND_WHITELIST = (
    "merge-comment",
    "verify-fix",
    "re-review",
    "ci-fix",
    "review",
    "address",
    "transition",
    "triage",
    "respond",
    "merge",
    "advisory",
    "vuln",
    "mention",
)

# Task line: `- [ ] kind:key — title <annotations>` or `- [x] ...`.
# The em-dash separates the ID from the title. Annotations are everything
# from the first ` via:`, ` linked:`, ` ➕`, ` 📅`, ` 🔁`, ` ✅`, ` source:`,
# ` attack:`, ` repro:`, or ` auto:` token onward.
TASK_LINE_RE = re.compile(
    r"^- \[(?P<check>[ x])\] "
    r"(?P<kind>[a-z-]+):(?P<key>\S+) "
    r"[—-] "
    r"(?P<rest>.*)$"
)

# Annotation token boundaries inside the `rest` capture.
ANNOTATION_KEYS = ("via:", "linked:", "source:", "attack:", "repro:", "auto:", "priority:", "file_ref:")
DATE_EMOJIS = ("➕", "📅", "🔁", "✅")

# Indented vuln continuation lines, e.g. "  - taint: blah" or "  - repro: blah".
VULN_SUB_RE = re.compile(r"^\s{2,}-\s*(?P<key>taint|repro):\s*(?P<val>.*)$")

# "Last refreshed: 2026-06-12" header lines.
HEADER_DATE_RE = re.compile(
    r"^(?:Last refreshed|last_diff_sha|area_cycle_index):\s*(?P<val>.*?)\s*$"
)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def split_title_and_annotations(rest: str) -> tuple[str, str]:
    """Split the post-ID `rest` into title and annotation tail.

    The annotation tail starts at the first token that looks like an
    annotation key (`via:`, `linked:`, `source:`, `attack:`, `repro:`,
    `auto:`) or a date emoji.
    """
    tokens = rest.split(" ")
    cut = len(tokens)
    for i, tok in enumerate(tokens):
        if tok in DATE_EMOJIS:
            cut = i
            break
        for k in ANNOTATION_KEYS:
            if tok.startswith(k):
                cut = i
                break
        if cut != len(tokens):
            break
    title = " ".join(tokens[:cut]).rstrip(" ,;")
    annotations = " ".join(tokens[cut:])
    return title, annotations


def parse_annotations(ann: str) -> dict:
    """Pull via/linked/source/attack/repro/auto + date emojis out of `ann`."""
    out: dict = {}
    if not ann:
        return out
    tokens = ann.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in DATE_EMOJIS and i + 1 < len(tokens):
            mapping = {
                "➕": "created",
                "📅": "due",
                "🔁": "refreshed",
                "✅": "closed",
            }
            out[mapping[tok]] = tokens[i + 1]
            i += 2
            continue
        matched = False
        for k in ANNOTATION_KEYS:
            if tok.startswith(k):
                field = k[:-1]  # drop trailing colon
                out[field] = tok[len(k):]
                matched = True
                break
        if not matched:
            # Unknown token. Skip silently; loops sometimes emit extras.
            pass
        i += 1
    return out


def filename_for(kind: str, key: str) -> str:
    """Apply the protocol's filename rules to a (kind, key) pair."""
    transformed = key.replace("→", "-")  # right-arrow → hyphen
    transformed = transformed.replace("#", "")
    transformed = re.sub(r"\s+", "-", transformed)
    return f"{kind}-{transformed}.md"


def yaml_quote(value: str) -> str:
    """Quote a YAML scalar when it contains characters that need it."""
    if value == "":
        return "''"
    needs_quote = (
        value.startswith("#")
        or value.startswith("@")
        or ":" in value
        or value.lower() in ("yes", "no", "true", "false", "null")
    )
    if needs_quote:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return value


def render_frontmatter(fm: dict, order: list[str]) -> str:
    """Render a dict as a YAML frontmatter block in the given key order."""
    lines = ["---"]
    for key in order:
        if key not in fm or fm[key] is None or fm[key] == "":
            continue
        lines.append(f"{key}: {yaml_quote(str(fm[key]))}")
    lines.append("---")
    return "\n".join(lines)


def find_header_refreshed(text: str) -> str | None:
    """Scan the top of an inbox file for a `Last refreshed: <date>` header."""
    for line in text.splitlines()[:10]:
        m = HEADER_DATE_RE.match(line)
        if m and "refreshed" in line.lower():
            d = ISO_DATE_RE.search(m.group("val"))
            if d:
                return d.group(1)
    return None


def parse_legacy_file(path: Path, inbox_label: str) -> list[dict]:
    """Walk one legacy inbox file and return parsed task dicts.

    Each dict carries the raw fields needed to render a task file:
    kind, key, title, status, via, linked, source, attack, repro, auto,
    created, due, refreshed, closed, inbox, taint_body, repro_body.
    """
    text = path.read_text(encoding="utf-8")
    header_refreshed = find_header_refreshed(text)
    tasks: list[dict] = []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = TASK_LINE_RE.match(line)
        if not m:
            i += 1
            continue

        check = m.group("check")
        kind = m.group("kind")
        key = m.group("key")
        rest = m.group("rest")

        if kind not in KIND_WHITELIST:
            print(
                f"warn: {path.name}:{i + 1}: unknown kind '{kind}', skipping",
                file=sys.stderr,
            )
            i += 1
            continue

        title, ann = split_title_and_annotations(rest)
        meta = parse_annotations(ann)

        status = "done" if check == "x" else "new"

        task = {
            "kind": kind,
            "key": key,
            "title": title,
            "status": status,
            "via": meta.get("via"),
            "linked": meta.get("linked"),
            "source": meta.get("source"),
            "attack": meta.get("attack"),
            "repro_ann": meta.get("repro"),
            "file_ref": meta.get("file_ref"),
            "priority": meta.get("priority"),
            "auto": meta.get("auto"),
            "created": meta.get("created"),
            "due": meta.get("due"),
            "refreshed": meta.get("refreshed"),
            "closed": meta.get("closed"),
            "inbox": inbox_label,
            "taint_body": None,
            "repro_body": None,
            "_source_line": i + 1,
            "_source_file": path.name,
        }

        # Vuln continuation lines.
        if kind == "vuln":
            j = i + 1
            while j < len(lines):
                sub = lines[j]
                if sub.strip() == "":
                    break
                sm = VULN_SUB_RE.match(sub)
                if not sm:
                    break
                if sm.group("key") == "taint":
                    task["taint_body"] = sm.group("val").strip()
                elif sm.group("key") == "repro":
                    task["repro_body"] = sm.group("val").strip()
                j += 1
            i = j
        else:
            i += 1

        # Defaults per spec 10.3.
        if not task["created"] and header_refreshed:
            task["created"] = header_refreshed
        if not task["refreshed"]:
            task["refreshed"] = task["created"]

        tasks.append(task)

    return tasks


def render_task_file(task: dict) -> str:
    """Build the markdown body (frontmatter + sections) for one task."""
    fm: dict = {
        "kind": task["kind"],
        "key": task["key"],
        "status": task["status"],
        "via": task["via"],
        "linked": task["linked"] or "none",
        "title": task["title"],
        "created": task["created"],
        "due": task["due"],
        "refreshed": task["refreshed"],
        "inbox": task["inbox"],
    }
    if task["closed"]:
        fm["closed"] = task["closed"]
    if task["source"]:
        fm["source"] = task["source"]
    if task.get("priority"):
        fm["priority"] = task["priority"]
    if task["auto"]:
        fm["auto"] = task["auto"]
    if task["kind"] == "vuln":
        # Vuln-only fields. Preserve the inline annotations from the
        # legacy two-line entries — these become required vuln frontmatter
        # per protocol.md.
        if task.get("attack"):
            fm["attack"] = task["attack"]
        if task.get("repro_ann"):
            fm["repro"] = task["repro_ann"]
        if task.get("file_ref"):
            fm["file_ref"] = task["file_ref"]

    order = [
        "kind",
        "key",
        "status",
        "via",
        "linked",
        "title",
        "created",
        "due",
        "refreshed",
        "closed",
        "source",
        "priority",
        "auto",
        "inbox",
        "attack",
        "repro",
        "file_ref",
    ]
    out = render_frontmatter(fm, order)

    if task["kind"] == "vuln":
        sections = []
        if task["taint_body"]:
            sections.append(f"## Taint\n\n{task['taint_body']}")
        else:
            print(
                f"warn: {task['_source_file']}:{task['_source_line']}: "
                f"vuln {task['key']} missing taint line",
                file=sys.stderr,
            )
        if task["repro_body"]:
            sections.append(f"## Repro\n\n{task['repro_body']}")
        else:
            print(
                f"warn: {task['_source_file']}:{task['_source_line']}: "
                f"vuln {task['key']} missing repro line",
                file=sys.stderr,
            )
        if sections:
            out += "\n\n" + "\n\n".join(sections)

    return out + "\n"


def validate_required(task: dict) -> bool:
    """Confirm a task has enough metadata to render. Warn and reject if not."""
    missing = []
    for field in ("via", "title", "created", "due", "refreshed"):
        if not task[field]:
            missing.append(field)
    if missing:
        print(
            f"warn: {task['_source_file']}:{task['_source_line']}: "
            f"{task['kind']}:{task['key']} missing {', '.join(missing)}, skipping",
            file=sys.stderr,
        )
        return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: migrate-from-line-based.py <inbox-dir>", file=sys.stderr)
        return 2

    inbox_dir = Path(argv[1]).expanduser().resolve()
    if not inbox_dir.is_dir():
        print(f"error: not a directory: {inbox_dir}", file=sys.stderr)
        return 2

    tasks_dir = inbox_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    sources = [
        (inbox_dir / "inbox-prs.md", "prs"),
        (inbox_dir / "inbox-tickets.md", "tickets"),
        (inbox_dir / "inbox-vulns.md", "vulns"),
    ]

    processed = 0
    written = 0
    skipped = 0

    for path, inbox_label in sources:
        if not path.exists():
            continue
        tasks = parse_legacy_file(path, inbox_label)
        for task in tasks:
            processed += 1
            if not validate_required(task):
                continue
            fname = filename_for(task["kind"], task["key"])
            out_path = tasks_dir / fname
            if out_path.exists():
                print(f"skipped: {out_path}")
                skipped += 1
                continue
            archive_path = tasks_dir / "archive" / fname
            if archive_path.exists() and task["status"] == "done":
                print(f"skipped: {archive_path} (already archived)")
                skipped += 1
                continue
            out_path.write_text(render_task_file(task), encoding="utf-8")
            written += 1

    print(f"\n{processed} processed, {written} written, {skipped} skipped")
    print(f"date: {date.today().isoformat()}")
    print("Originals untouched. Once verified, rm them manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
