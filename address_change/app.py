#!/usr/bin/env python3
"""Address Change Manager — zero-dependency web app.

A self-hosted tracker for everything that needs updating when you move
house: a pre-built master checklist (banks, government, utilities,
insurance, subscriptions, …), per-item status and notes, links to each
provider's official change-of-address page, and a generated notification
letter pre-filled with your details.

Run with::

    python address_change/app.py            # http://localhost:8000
    python address_change/app.py --port 9000

State persists to ``address_change/data.json`` (gitignored). Stdlib only —
no pip installs needed.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from checklist import CATEGORIES, MASTER_CHECKLIST, WHEN_ASAP

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_FILE = BASE_DIR / "data.json"

VALID_STATUSES = {"todo", "in_progress", "done", "na"}

_lock = threading.Lock()


def _default_state() -> dict:
    return {
        "move": {
            "name": "",
            "old_address": "",
            "new_address": "",
            "move_date": "",
            "phone": "",
            "email": "",
        },
        "items": [dict(item) for item in MASTER_CHECKLIST],
        "categories": CATEGORIES,
    }


def load_state() -> dict:
    if DATA_FILE.exists():
        with DATA_FILE.open() as f:
            state = json.load(f)
        # Merge in master items added since the data file was created.
        known = {item["id"] for item in state["items"]}
        for item in MASTER_CHECKLIST:
            if item["id"] not in known:
                state["items"].append(dict(item))
        state["categories"] = CATEGORIES
        return state
    return _default_state()


def save_state(state: dict) -> None:
    tmp = DATA_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(DATA_FILE)


STATE = load_state()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # -- helpers -----------------------------------------------------------
    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length))

    def _find_item(self, item_id):
        for item in STATE["items"]:
            if item["id"] == item_id:
                return item
        return None

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (args[0] if args else ""):
            return
        super().log_message(fmt, *args)

    # -- routes --------------------------------------------------------------
    def do_GET(self):
        if self.path == "/api/state":
            with _lock:
                self._json(STATE)
        else:
            super().do_GET()

    def do_PUT(self):
        if self.path == "/api/move":
            body = self._read_body()
            with _lock:
                for key in STATE["move"]:
                    if key in body:
                        STATE["move"][key] = str(body[key])
                save_state(STATE)
                self._json(STATE["move"])
        else:
            self._json({"error": "not found"}, 404)

    def do_PATCH(self):
        match = re.fullmatch(r"/api/items/([\w-]+)", self.path)
        if not match:
            self._json({"error": "not found"}, 404)
            return
        body = self._read_body()
        with _lock:
            item = self._find_item(match.group(1))
            if item is None:
                self._json({"error": "unknown item"}, 404)
                return
            if "status" in body:
                if body["status"] not in VALID_STATUSES:
                    self._json({"error": "bad status"}, 400)
                    return
                item["status"] = body["status"]
            if "notes" in body:
                item["notes"] = str(body["notes"])
            save_state(STATE)
            self._json(item)

    def do_POST(self):
        global STATE
        if self.path == "/api/items":
            body = self._read_body()
            name = str(body.get("name", "")).strip()
            category = body.get("category", "People & other")
            if not name:
                self._json({"error": "name required"}, 400)
                return
            if category not in CATEGORIES:
                category = "People & other"
            item = {
                "id": f"custom-{uuid.uuid4().hex[:8]}",
                "name": name,
                "category": category,
                "when": WHEN_ASAP,
                "hint": str(body.get("hint", "")).strip(),
                "link": str(body.get("link", "")).strip() or None,
                "status": "todo",
                "notes": "",
                "custom": True,
            }
            with _lock:
                STATE["items"].append(item)
                save_state(STATE)
                self._json(item, 201)
        elif self.path == "/api/reset":
            with _lock:
                STATE = _default_state()
                save_state(STATE)
                self._json(STATE)
        else:
            self._json({"error": "not found"}, 404)

    def do_DELETE(self):
        match = re.fullmatch(r"/api/items/([\w-]+)", self.path)
        if not match:
            self._json({"error": "not found"}, 404)
            return
        with _lock:
            item = self._find_item(match.group(1))
            if item is None:
                self._json({"error": "unknown item"}, 404)
                return
            if not item["custom"]:
                self._json({"error": "only custom items can be deleted; "
                            "mark built-in items N/A instead"}, 400)
                return
            STATE["items"].remove(item)
            save_state(STATE)
            self._json({"deleted": item["id"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Address Change Manager → http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
