#!/usr/bin/env python3
"""Build the server-free artifacts from the master checklist.

Generates:

- ``standalone.html`` — the full interactive app in a single file. Open it
  directly in any browser (no server, no Python); progress is saved in the
  browser's localStorage.
- ``CHECKLIST.md`` — a plain, printable Markdown version of the checklist.

Run after editing ``checklist.py`` or anything in ``static/``::

    python address_change/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

from checklist import CATEGORIES, MASTER_CHECKLIST

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

WHEN_ORDER = [
    "As soon as date is known",
    "1–2 weeks before",
    "Moving week",
    "After the move",
]


def build_standalone() -> Path:
    html = (STATIC_DIR / "index.html").read_text()
    css = (STATIC_DIR / "style.css").read_text()
    js = (STATIC_DIR / "app.js").read_text()

    master = {
        "move": {"name": "", "old_address": "", "new_address": "",
                 "move_date": "", "phone": "", "email": ""},
        "items": MASTER_CHECKLIST,
        "categories": CATEGORIES,
    }
    # "</" must not appear inside a <script> block.
    data = json.dumps(master, ensure_ascii=False).replace("</", "<\\/")

    html = html.replace(
        '<link rel="stylesheet" href="style.css">',
        f"<style>\n{css}</style>",
    )
    html = html.replace(
        '<script src="app.js"></script>',
        f"<script>window.MASTER_DATA = {data};</script>\n"
        f"<script>\n{js}</script>",
    )
    html = html.replace(
        "tracked in one place.</p>",
        "tracked in one place. Standalone version — progress is saved in "
        "this browser.</p>",
    )

    out = BASE_DIR / "standalone.html"
    out.write_text(html)
    return out


def build_markdown() -> Path:
    lines = [
        "# Moving home — the complete address-change checklist",
        "",
        "Everything that needs your new address when you move, grouped by "
        "category. Timing key: do items in *(As soon as date is known)* "
        "first, then *(1–2 weeks before)*, *(Moving week)*, and "
        "*(After the move)*.",
        "",
        "> Generated from [`checklist.py`](checklist.py) by "
        "[`build.py`](build.py). For the interactive version run "
        "`python address_change/app.py`, or just open "
        "[`standalone.html`](standalone.html) in a browser.",
        "",
    ]
    for category in CATEGORIES:
        items = [i for i in MASTER_CHECKLIST if i["category"] == category]
        items.sort(key=lambda i: WHEN_ORDER.index(i["when"]))
        lines.append(f"## {category}")
        lines.append("")
        for item in items:
            name = (f"[{item['name']}]({item['link']})" if item["link"]
                    else item["name"])
            lines.append(f"- [ ] **{name}** *({item['when']})* — "
                         f"{item['hint']}")
        lines.append("")

    out = BASE_DIR / "CHECKLIST.md"
    out.write_text("\n".join(lines))
    return out


if __name__ == "__main__":
    for path in (build_standalone(), build_markdown()):
        print(f"wrote {path.relative_to(BASE_DIR.parent)} "
              f"({path.stat().st_size:,} bytes)")
