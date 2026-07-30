---
name: obsidian
description: Read, search, and summarize the user's local Obsidian vault at D:\文档\08-Obsidian. Use when the user asks to query Obsidian, read notes, search the vault, find documents or markdown content, inspect backlinks/frontmatter/tags, summarize vault material, or use Obsidian CLI-style access to retrieve knowledge from their repository.
---

# Obsidian Vault Access

Use this skill to retrieve information from the user's local Obsidian vault:

`D:\文档\08-Obsidian`

Prefer the bundled CLI helper for deterministic local reads:

```powershell
python "C:\Users\w33938\.codex\skills\obsidian\scripts\obsidian_cli.py" search "keyword"
python "C:\Users\w33938\.codex\skills\obsidian\scripts\obsidian_cli.py" read "01-笔记/example.md"
```

## Workflow

1. Use `search` first when the user asks for information but does not name an exact note.
2. Use `read` for exact files returned by search, then answer from the retrieved note text.
3. Use `list` to inspect note paths when search terms are uncertain.
4. Use `tags` or `frontmatter` when the user asks about organization, metadata, or tagged topics.
5. Do not modify vault files unless the user explicitly asks to edit Obsidian notes.
6. Treat `.obsidian/`, plugin folders, attachments, caches, and non-text assets as support files; avoid reading them unless directly relevant.

## CLI Helper

Script:

`scripts/obsidian_cli.py`

Commands:

- `list [--limit N] [--json]`: List Markdown notes relative to the vault root.
- `search <query> [--limit N] [--json]`: Search Markdown files by filename and body text.
- `read <relative-path> [--max-chars N] [--json]`: Print note content.
- `tags [--json]`: Extract hashtags from Markdown note bodies.
- `frontmatter <relative-path> [--json]`: Print YAML frontmatter for one note.

The helper confines reads to the vault root and ignores common Obsidian/internal folders by default.

If a real `obsidian` command is installed and the user asks to open the app or a note URI, use it only for app-level actions. For content retrieval, prefer local filesystem reads through this helper because Obsidian's desktop CLI is not a reliable text extraction interface.

## Answering From Notes

- Cite note paths in plain text when summarizing, for example `01-笔记/foo.md`.
- If search returns many possible matches, read the most relevant few before answering.
- If no note matches, say that the vault search did not find a match and mention the query used.
- Preserve Chinese text exactly when quoting short snippets, but keep quotes brief.
