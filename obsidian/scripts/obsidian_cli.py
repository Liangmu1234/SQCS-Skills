#!/usr/bin/env python3
"""Small CLI for reading a local Obsidian vault."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(r"D:\文档\08-Obsidian").resolve()
IGNORE_PARTS = {".obsidian", ".trash", ".git", "__pycache__"}
DEFAULT_LIMIT = 20


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def ensure_vault() -> None:
    if not VAULT_ROOT.exists():
        fail(f"vault not found: {VAULT_ROOT}")
    if not VAULT_ROOT.is_dir():
        fail(f"vault path is not a directory: {VAULT_ROOT}")


def safe_path(relative_path: str) -> Path:
    candidate = (VAULT_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(VAULT_ROOT)
    except ValueError:
        fail("path escapes the Obsidian vault")
    return candidate


def is_ignored(path: Path) -> bool:
    try:
        rel = path.relative_to(VAULT_ROOT)
    except ValueError:
        return True
    return any(part in IGNORE_PARTS for part in rel.parts)


def note_paths() -> list[Path]:
    ensure_vault()
    return sorted(
        path
        for path in VAULT_ROOT.rglob("*.md")
        if path.is_file() and not is_ignored(path)
    )


def rel(path: Path) -> str:
    return path.relative_to(VAULT_ROOT).as_posix()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    paths = [rel(path) for path in note_paths()]
    if args.limit:
        paths = paths[: args.limit]
    if args.json:
        print_json({"vault": str(VAULT_ROOT), "count": len(paths), "notes": paths})
    else:
        for path in paths:
            print(path)


def score_match(query: str, path: Path, text: str) -> tuple[int, list[str]]:
    hay_path = rel(path).lower()
    hay_text = text.lower()
    terms = [term for term in re.split(r"\s+", query.lower().strip()) if term]
    score = 0
    snippets: list[str] = []
    for term in terms:
        if term in hay_path:
            score += 8
        idx = hay_text.find(term)
        if idx >= 0:
            score += 3
            start = max(0, idx - 60)
            end = min(len(text), idx + len(term) + 100)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            snippets.append(snippet)
    return score, snippets[:3]


def cmd_search(args: argparse.Namespace) -> None:
    results = []
    for path in note_paths():
        text = read_text(path)
        score, snippets = score_match(args.query, path, text)
        if score:
            results.append(
                {
                    "path": rel(path),
                    "score": score,
                    "snippets": snippets,
                }
            )
    results.sort(key=lambda item: (-item["score"], item["path"]))
    results = results[: args.limit]
    if args.json:
        print_json({"query": args.query, "count": len(results), "results": results})
    else:
        for item in results:
            print(f"{item['path']}  score={item['score']}")
            for snippet in item["snippets"]:
                print(f"  {snippet}")


def cmd_read(args: argparse.Namespace) -> None:
    path = safe_path(args.path)
    if not path.exists() or not path.is_file():
        fail(f"note not found: {args.path}")
    if path.suffix.lower() != ".md":
        fail("read expects a Markdown .md note")
    text = read_text(path)
    truncated = False
    if args.max_chars and len(text) > args.max_chars:
        text = text[: args.max_chars]
        truncated = True
    if args.json:
        print_json({"path": rel(path), "truncated": truncated, "content": text})
    else:
        print(text)
        if truncated:
            print("\n[truncated]", file=sys.stderr)


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def cmd_frontmatter(args: argparse.Namespace) -> None:
    path = safe_path(args.path)
    if not path.exists() or not path.is_file():
        fail(f"note not found: {args.path}")
    frontmatter = extract_frontmatter(read_text(path))
    if args.json:
        print_json({"path": rel(path), "frontmatter": frontmatter})
    else:
        print(frontmatter)


def cmd_tags(args: argparse.Namespace) -> None:
    tag_re = re.compile(r"(?<!\w)#([\w\-/\u4e00-\u9fff]+)")
    tags: dict[str, list[str]] = {}
    for path in note_paths():
        for tag in sorted(set(tag_re.findall(read_text(path)))):
            tags.setdefault(f"#{tag}", []).append(rel(path))
    if args.json:
        print_json({"count": len(tags), "tags": tags})
    else:
        for tag in sorted(tags):
            print(f"{tag} ({len(tags[tag])})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and search an Obsidian vault.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List Markdown notes.")
    list_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=cmd_list)

    search_parser = sub.add_parser("search", help="Search note paths and contents.")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(func=cmd_search)

    read_parser = sub.add_parser("read", help="Read one Markdown note.")
    read_parser.add_argument("path")
    read_parser.add_argument("--max-chars", type=int, default=30000)
    read_parser.add_argument("--json", action="store_true")
    read_parser.set_defaults(func=cmd_read)

    tags_parser = sub.add_parser("tags", help="List hashtags in the vault.")
    tags_parser.add_argument("--json", action="store_true")
    tags_parser.set_defaults(func=cmd_tags)

    fm_parser = sub.add_parser("frontmatter", help="Print YAML frontmatter for one note.")
    fm_parser.add_argument("path")
    fm_parser.add_argument("--json", action="store_true")
    fm_parser.set_defaults(func=cmd_frontmatter)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
