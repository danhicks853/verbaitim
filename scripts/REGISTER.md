# Registering the VerbAItim automation on BEAST

Two scheduled tasks: **Prep** (1:44 AM, T-30) and **Post** (2:14 AM). Prep does
all the slow/fallible work and writes a freeze marker; Post reads the marker and
does the one sacred thing. See the script headers for the full contract.

## Prerequisites (once, on BEAST)

1. **Python + Pillow**
   ```powershell
   python -m pip install pillow
   ```
2. **Credential files** (both gitignored — never in the repo; pull from 1Password):
   - `scripts\.bluesky_credentials`
     ```
     BLUESKY_HANDLE=readverbaitim.bsky.social
     BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
     ```
   - `scripts\.resend_credentials`
     ```
     RESEND_API_KEY=re_xxxxxxxx
     MAIL_TO=read.verbaitim@gmail.com
     MAIL_FROM=onboarding@resend.dev
     ```
3. **Git push must work non-interactively** as the task's user (session 0).
   Test it the way the task will run it — see "Session-0 git" below.

## Register the tasks

```powershell
schtasks /create /tn "VerbAItim-Prep" /xml "D:\github\verbaitim\scripts\tasks\VerbAItim-Prep.xml" /ru "BEAST\daniel.hicks" /rp *
schtasks /create /tn "VerbAItim-Post" /xml "D:\github\verbaitim\scripts\tasks\VerbAItim-Post.xml" /ru "BEAST\daniel.hicks" /rp *
```
`/rp *` prompts for the password once so the task can run **whether logged on or
not** (session 0, survives sign-out). Confirm the XML `<UserId>` matches the real
`BEAST\<user>` — edit if the hostname/user differs.

## Enable Task Scheduler history
Task Scheduler Library -> right pane -> **Enable All Tasks History**. Off by
default; without it there's no forensic trail when a run misbehaves.

## Break-in: prove it signed-out BEFORE trusting it asleep

First live fire is **0003**. Do NOT just enable and walk away — validate:

1. **Manual prep, watched:**
   ```powershell
   python scripts\prep.py
   ```
   Expect: exit 0, a `render_output\.freeze` file, a "prep ✓ ready 0003" email.
2. **Manual post, watched:**
   ```powershell
   python scripts\post.py
   ```
   Expect: 0003 live on Bluesky, cursor -> 0003, freeze cleared, heartbeat email,
   push succeeded.
   *(This consumes 0003. That's fine — it's a real post, just done by hand while
   watching. The automation takes over cleanly from 0004.)*
3. **Signed-out test (the one that matters):** re-arm with the next bit, then
   **sign out of BEAST** and let the scheduled Prep + Post fire on their own.
   Next morning: confirm from your phone it posted, and from the automation.log +
   the heartbeat email that both tasks ran in session 0. THIS is the test that
   catches session-0 credential failures. Don't skip it.

## Session-0 git (the likely silent failure)
`gh auth` login is user-scoped and may not be visible to a session-0 task.
If Post's push fails signed-out but works signed-in, that's this. Fix: configure
a credential helper or a PAT/deploy key that works without an interactive login.
The post still SUCCEEDS if push fails (cursor is local-authoritative) — you'll
just get a "push failed" note in the heartbeat and must sync manually. Fix before
relying on laptop<->BEAST sync.

## Kill switch
```powershell
schtasks /change /tn "VerbAItim-Post" /disable
schtasks /change /tn "VerbAItim-Prep" /disable
```
