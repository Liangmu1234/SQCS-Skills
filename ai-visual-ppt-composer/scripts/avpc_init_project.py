#!/usr/bin/env python3
"""Create a working project for AI Visual PPT Composer.

The generated project contains:
- deck.json sample
- local scripts copied from the skill
- package.json with PPTXGenJS and optional Playwright dependency
- output directories
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def skill_root_from_this_file() -> Path:
    return Path(__file__).resolve().parents[1]


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold an AI Visual PPT Composer project")
    parser.add_argument("--target", type=Path, default=Path("./avpc-project"), help="Project directory to create")
    parser.add_argument("--title", default="AI Visual PPT", help="Deck title")
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files")
    args = parser.parse_args()

    root = skill_root_from_this_file()
    target = args.target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    for rel in ["assets/backgrounds", "assets/images", "assets/icons", "output", "scripts", "references"]:
        (target / rel).mkdir(parents=True, exist_ok=True)

    # Copy scripts and references.
    for src in (root / "scripts").glob("*"):
        if src.is_file():
            dst = target / "scripts" / src.name
            if args.force or not dst.exists():
                shutil.copy2(src, dst)
    for src in (root / "references").glob("*"):
        if src.is_file():
            dst = target / "references" / src.name
            if args.force or not dst.exists():
                shutil.copy2(src, dst)

    sample_path = root / "assets" / "sample_deck.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample["meta"]["title"] = args.title
    deck_path = target / "deck.json"
    if args.force or not deck_path.exists():
        write_json(deck_path, sample)

    package_json = {
        "name": "avpc-project",
        "version": "0.1.0",
        "private": True,
        "type": "module",
        "scripts": {
            "validate": "python scripts/avpc_validate_deck.py deck.json",
            "build": "node scripts/avpc_build.mjs deck.json output",
            "build:no-screenshots": "node scripts/avpc_build.mjs deck.json output --no-screenshots"
        },
        "dependencies": {
            "pptxgenjs": "latest"
        },
        "devDependencies": {
            "playwright": "latest"
        }
    }
    pkg_path = target / "package.json"
    if args.force or not pkg_path.exists():
        write_json(pkg_path, package_json)

    readme = f"""# {args.title}

This project was scaffolded by `ai-visual-ppt-composer`.

## Run

```bash
npm install
npm run validate
npm run build
```

Outputs go to `output/`:

- `deck.pptx`: editable PowerPoint
- `deck_preview.html`: browser preview
- `slide-XX.png`: preview screenshots if Playwright is installed

## Edit

Edit `deck.json`. Keep all meaningful text as `type: \"text\"` elements.
Use `background.image` only for no-text visual backgrounds.
"""
    readme_path = target / "README.md"
    if args.force or not readme_path.exists():
        readme_path.write_text(readme, encoding="utf-8")

    gitignore = "node_modules/\noutput/*.png\noutput/*.pptx\n.DS_Store\n"
    gi_path = target / ".gitignore"
    if args.force or not gi_path.exists():
        gi_path.write_text(gitignore, encoding="utf-8")

    print(f"Created AVPC project at: {target}")
    print("Next steps:")
    print(f"  cd {target}")
    print("  npm install")
    print("  npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
