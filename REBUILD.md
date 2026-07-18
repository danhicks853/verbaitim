# Rebuilding VerbAItim on a fresh/wiped machine

The repo holds the machinery; secrets live in 1Password. A rebuild is
clone + inject two secrets + install prerequisites + register tasks.

## 1. Clone
```powershell
gh repo clone danhicks853/verbaitim D:\github\verbaitim
cd D:\github\verbaitim
```
(Path `D:\github\verbaitim` is assumed throughout the scripts/XMLs. If you
clone elsewhere, update `$repo` in prep.ps1/post.ps1 and the `<Command>`/paths
in scripts\tasks\*.xml.)

## 2. Prerequisites
```powershell
python -m pip install pillow
```
Python 3 + Pillow is the only runtime dependency (Pillow is NOT vendored).
Fonts ARE vendored in scripts\fonts\, so rendering needs nothing else.

## 3. Inject secrets (from 1Password — never committed)
Create both files (see scripts\REGISTER.md for exact keys):
- `scripts\.bluesky_credentials`  (handle + app password)
- `scripts\.resend_credentials`   (Resend key + MAIL_TO + MAIL_FROM)
Both are gitignored. Confirm:
```powershell
git check-ignore scripts\.bluesky_credentials scripts\.resend_credentials
```
(should echo both paths back = correctly ignored)

## 4. Git line endings
`.gitattributes` pins this (LF for .py/.md, CRLF for .ps1). Nothing to do —
just don't fight it. If the whole tree ever shows "modified" after a checkout,
that's an EOL issue: `git add --renormalize .` and inspect with
`git diff --ignore-all-space` before committing.

## 5. Register scheduled tasks
Follow scripts\REGISTER.md (schtasks import, history, break-in, session-0 git).

## 6. Sanity check the cursor
```powershell
Get-Content bits\.cursor
```
This machine must match the true last-posted bit before enabling the Post task,
or it will re-post. If unsure, `git pull` and trust the pushed cursor.

## Component map
- `bits/NNNN-*.md`           the content (tracked)
- `bits/.cursor`             last-posted number (tracked)
- `raw/`                     unprocessed clips (GITIGNORED, never committed)
- `render_output/`           PNGs, .freeze, clean.md, automation.log (GITIGNORED)
- `scripts/render_bit.py`    Pillow renderer (bit .md -> PNG card)
- `scripts/verbaitim_core.py` shared helpers (creds/cursor/freeze/mail/bluesky)
- `scripts/prep.py`          T-30: pull, preflight, render, freeze, low-inv alert
- `scripts/post.py`          2:14: read freeze, post, advance, push, heartbeat
- `scripts/post_next.py`     ORIGINAL one-shot manual poster (kept for hand-posting)
- `scripts/*.ps1`            Task Scheduler entrypoints
- `scripts/tasks/*.xml`      scheduled-task definitions
- `scripts/.*_credentials`   secrets (GITIGNORED)
