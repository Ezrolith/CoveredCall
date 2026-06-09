# Address Change Manager

A self-hosted web app that tracks **everything you need to update when moving
home** — banks, government records, utilities, insurance, health,
subscriptions and more — in one checklist.

> **Why a tracker and not full automation?** Banks and government bodies do
> not expose public APIs for changing your registered address, and any tool
> that logged into your accounts with your credentials would breach their
> terms (and be a security hazard). What *can* be automated is everything
> around the process — and this app does that:
>
> - a complete, pre-built master checklist (~50 items, UK-leaning with
>   generic items that apply anywhere)
> - direct links to each provider's official change-of-address page
> - per-item status (to do / in progress / done / N/A) and private notes
> - a notification letter auto-filled with your old/new address, ready to
>   paste into any web form, email or post
> - progress bar, moving-day countdown, search/filter, custom items, CSV export

## Three ways to use it

**1. No server at all — open [`standalone.html`](standalone.html) in any
browser.** The whole app in a single file; your progress is saved in that
browser's localStorage. This is the easiest option: download the file and
double-click it.

**2. Just read the list — [`CHECKLIST.md`](CHECKLIST.md).** A plain,
printable Markdown version of the full checklist with timing and links.

**3. Run the server** (no dependencies beyond Python 3.9+ — stdlib only):

```bash
python address_change/app.py          # http://localhost:8000
python address_change/app.py --port 9000
```

Open the printed URL in a browser. Your data persists to
`address_change/data.json` (gitignored — it contains your addresses, keep it
private).

`standalone.html` and `CHECKLIST.md` are generated — after editing
`checklist.py` or anything in `static/`, regenerate them with
`python address_change/build.py`.

## How to use it

1. Fill in **Your move** (name, old/new address, moving date) and save.
2. Work through the checklist — each item shows *when* to do it
   (as soon as the date is known → 1–2 weeks before → moving week → after).
3. Click **Open site ↗** on an item to jump to the provider's official
   change-of-address page, and **Copy notification letter** to paste your
   pre-filled details.
4. Mark items done, jot reference numbers in the notes, add anything
   missing with **+ Add item**, and watch the progress bar fill up.

## API

The frontend uses a small JSON API you can also script against:

| Method   | Path              | Purpose                                  |
|----------|-------------------|------------------------------------------|
| GET      | `/api/state`      | Full state (move details + all items)    |
| PUT      | `/api/move`       | Update move details                      |
| PATCH    | `/api/items/<id>` | Update an item's `status` and/or `notes` |
| POST     | `/api/items`      | Add a custom item                        |
| DELETE   | `/api/items/<id>` | Delete a custom item                     |
| POST     | `/api/reset`      | Reset everything to the master checklist |

The master checklist lives in [`checklist.py`](checklist.py) — edit it to
change the defaults for everyone, or just add custom items in the UI.
