#!/usr/bin/env python3
"""
VerbAItim T-30 PREP  (scheduled ~1:44 AM local, 30 min before the post).

Does everything slow, fallible, or network-bound HERE, well clear of the
2:14 window, so post.py can be a near-instant local read + one API call.

Order (nothing here is time-critical; correctness over speed):
  1. git pull            -- sync cursor/bits from other machines (best-effort)
  2. preflight creds     -- prove Bluesky + Resend actually work RIGHT NOW,
                            while there's still 30 min to react to a rotted key
  3. resolve next bit    -- from cursor; abort cleanly if nothing to post
  4. render the PNG      -- CPU work moved out of the sacred window
  5. write .freeze       -- the contract post.py checks at 2:14
  6. low-inventory alert -- email if <= threshold bits remain
  7. email outcome       -- always, so a missing prep email is itself a signal

Exit codes: 0 = ready (freeze written), 2 = nothing to post (clean skip),
1 = failure (freeze NOT written -> post.py will abort tonight).

Pull policy (Dan's ruling): a failed pull is a WARNING, not a stop. Posting
only ever happens on BEAST, so local cursor is authoritative; a transient
GitHub hiccup must not cost a night. We warn-and-proceed from local state.
The warning rides in the success email -- which is WHY prep must heartbeat on
success: kill that email and a "posted from local, sync diverging" failure
goes silent.

CONTENT IS NOT THIS SCRIPT'S JOB. Cleaning, redaction, funny/safety calls all
happen at clip time in a control-room session. Prep renders whatever is in the
bit .md as-is. This is ops prep, not an editor.
"""

import os
import sys
import time
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verbaitim_core as vc  # noqa: E402
import render_bit  # noqa: E402

PULL_TIMEOUT = 60  # seconds; generous for a healthy pull, safe vs. the 30-min runway


def log(msg):
    print(f"[prep {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def git(args, timeout):
    return subprocess.run(
        ["git", "-C", vc.REPO] + args,
        capture_output=True, text=True, timeout=timeout,
    )


def main():
    warnings = []
    t0 = time.perf_counter()

    # 1. PULL (best-effort; warn, never stop) -------------------------------
    try:
        r = git(["pull", "--ff-only"], PULL_TIMEOUT)
        if r.returncode != 0:
            warnings.append(f"git pull failed (rc={r.returncode}): {r.stderr.strip()}")
            log(f"WARN pull failed, proceeding from local: {r.stderr.strip()}")
        else:
            log(f"pull ok: {r.stdout.strip() or 'already current'}")
    except subprocess.TimeoutExpired:
        warnings.append(f"git pull timed out after {PULL_TIMEOUT}s; proceeding from local")
        log("WARN pull timed out, proceeding from local")

    # 2. PREFLIGHT CREDS (fail loud NOW, 30 min of runway) ------------------
    bsky_ok, bsky_detail = vc.preflight_bluesky()
    if not bsky_ok:
        return fail(f"Bluesky preflight FAILED: {bsky_detail}", warnings)
    log(f"bluesky preflight ok (did={bsky_detail})")

    resend_ok, resend_detail = vc.send_mail(
        "VerbAItim prep — preflight",
        "Preflight mail check from T-30 prep. If you got this, Resend works.",
    )
    if not resend_ok:
        # Can't email the failure if email is what's broken -> exit nonzero,
        # rely on the ABSENT-heartbeat rule (no prep mail = go look).
        log(f"Resend preflight FAILED: {resend_detail}")
        return 1
    log(f"resend preflight ok ({resend_detail})")

    # 3. RESOLVE NEXT BIT ---------------------------------------------------
    cursor = vc.read_cursor()
    num, bit_path = vc.next_bit(cursor)
    if num is None:
        msg = f"Nothing to post: cursor at {cursor:04d}, no newer bit exists. BACKLOG EMPTY."
        log(msg)
        vc.send_mail("VerbAItim ⚠ BACKLOG EMPTY — no post tonight", msg)
        return 2  # clean skip, not a failure
    log(f"next bit: {num:04d} ({os.path.basename(bit_path)})")

    # 4. RENDER (out of the sacred window) ----------------------------------
    # Renders the bit AS-IS. Content integrity -- cleaning UI artifacts,
    # redaction, the funny/safety calls -- is Dan's job at clip time, in a
    # control-room session. This is ops prep, not an editor.
    try:
        os.makedirs(vc.RENDER_DIR, exist_ok=True)
        tag = f"{num:04d}"
        png_path = os.path.join(vc.RENDER_DIR, f"{tag}.png")
        render_bit.render(bit_path, png_path, tag=tag)
        if not os.path.exists(png_path):
            return fail(f"render produced no file at {png_path}", warnings)
        log(f"rendered {png_path}")
    except Exception as e:  # noqa: BLE001
        return fail(f"render FAILED for {num:04d}: {e}", warnings)

    # 5. WRITE FREEZE MARKER ------------------------------------------------
    vc.write_freeze(num, bit_path, png_path)
    log("freeze marker written")

    # 6. LOW-INVENTORY ALERT ------------------------------------------------
    remaining = vc.remaining_count(cursor)
    if remaining <= vc.LOW_INVENTORY_THRESHOLD:
        vc.send_mail(
            f"VerbAItim ⚠ LOW BACKLOG — {remaining} bits left",
            f"After tonight's {num:04d}, only {remaining - 1} remain queued.\n"
            f"Time to scrape/process more before the drip runs dry.",
        )
        log(f"low-inventory alert sent ({remaining} remaining)")

    # 7. OUTCOME EMAIL (always -- see module docstring on why success must email)
    elapsed = time.perf_counter() - t0
    warn_block = ("\n\nWARNINGS:\n- " + "\n- ".join(warnings)) if warnings else ""
    vc.send_mail(
        f"VerbAItim prep ✓ ready {num:04d}",
        f"Prep complete in {elapsed:.1f}s. {num:04d} rendered and frozen; "
        f"post.py will fire at 2:14.\n{remaining} bits remain (incl. tonight)."
        f"{warn_block}",
    )
    log(f"PREP OK in {elapsed:.1f}s; ready to post {num:04d}")
    return 0


def fail(msg, warnings):
    log(f"FAIL: {msg}")
    vc.clear_freeze()  # ensure post.py aborts rather than acting on stale state
    warn_block = ("\n\nEarlier warnings:\n- " + "\n- ".join(warnings)) if warnings else ""
    vc.send_mail("VerbAItim prep ✗ FAILED", f"{msg}{warn_block}\n\nNo post will go out at 2:14.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
