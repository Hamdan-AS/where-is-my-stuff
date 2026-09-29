# UI iteration copy

A working copy of the Django application, made for UI work. The Django app in this folder
is the authoritative implementation; there is no other copy to keep in sync.

## Run

```bash
cd /home/elite/sandbox/where-is-my-stuff-ui_iter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8086
```

If `.venv` is absent, `python3 -m venv .venv` creates it. The console scripts in a copied
`.venv` hardcode the original path, so create a fresh one here rather than copying it.

## What is in here

- The app: `config/`, `core/`, `templates/`, `static/`, and `db.sqlite3` with the existing
  demo data and private answers. Keep `db.sqlite3` at mode 600.
- `docs/WIREFRAME-BRIEF.md` — written spec of all thirteen screens, written to be handed
  to an image generation model.
- `docs/cs326-legacy/` — the CS-326 documentation filing, describing the removed PHP
  implementation.

## Removed on 29-09-2026

`files.zip`, `ui-previews/`, and `.playwright-mcp/` held five CSS styling directions
(`full-bleed-field-report`, `ledger`, `signal-board`, `quiet-directory`, `match-signal`),
their comparison page, and 33 screenshots and console logs. They were exploration output
for a design pass that was never adopted, and the archive at git commit `54fa6fc` still
has them. The `ui-wireframes-redesign.png` and `map-screens-wireframe.png` images they
were compared against were removed as well.

## Notes before you edit

- `db.sqlite3` here holds full 13-digit CNICs and 16-digit card numbers in private
  answers. Keep it at mode 600 and do not commit it.
- The five changes listed for `static/app.css` have not been applied. They were described
  in a conversation and never written to a file, so this file and that conversation are
  the only record. Write them down here before acting on them, or drop them.
