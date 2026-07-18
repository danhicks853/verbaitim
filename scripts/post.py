#!/usr/bin/env python3
"""
VerbAItim POST  (scheduled 2:14 AM local -- the sacred window).

Does the BAREST possible thing: read the freeze marker prep.py left, confirm
it's fresh and its PNG exists, POST, then advance the cursor. Everything
non-load-bearing (commit, push, heartbeat) happens AFTER the post succeeds,
so nothing can delay or sabotage the one act that matters.

NO network I/O before the post except the post itself -- the pull and render
already happened at T-30. If the freeze is missing/stale, prep failed; we
abort and email rather than improvise in the sacred window.

Idempotency: the cursor advances ONLY after a confirmed post, written locally
BEFORE the push. A failed push is a sync problem for tomorrow, never a reason
to re-post. A re-run after a successful post sees the advanced cursor +
cleared freeze and does nothing.

Exit codes: 0 = posted, 2 = nothing to do / clean abort, 1 = failure.
"""

import os
import sys
import time
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verbaitim_core as vc  # noqa: E402

PUSH_TIMEOUT = 60


def log(msg):
    print(f"[post {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def git(args, timeout):
    return subprocess.run(
        ["git", "-C", vc.REPO] + args,
        capture_output=True, text=True, timeout=timeout,
    )


def abort(msg):
    log(f"ABORT: {msg}")
    vc.send_mail("VerbAItim post ✗ ABORTED — no post tonight", msg)
    return 2


def main():
    t0 = time.perf_counter()

    # 1. READ + VALIDATE FREEZE (the gate) ----------------------------------
    marker = vc.read_freeze()
    if marker is None:
        return abort("No freeze marker. T-30 prep did not complete; nothing to post.")

    age = vc.freeze_age_seconds(marker)
    if age > vc.FREEZE_MAX_AGE_SECONDS:
        return abort(
            f"Freeze marker is stale ({age/60:.1f} min old, max "
            f"{vc.FREEZE_MAX_AGE_SECONDS/60:.0f}). Prep likely didn't run tonight."
        )

    num = marker["num"]
    tag = marker["tag"]
    bit_path = marker["bit_path"]
    png_path = marker["png_path"]

    # Guard against double-post: freeze must match the actual next bit.
    cursor = vc.read_cursor()
    if num <= cursor:
        vc.clear_freeze()
        return abort(f"Freeze says {tag} but cursor already at {cursor:04d}. "
                     f"Already posted; clearing stale freeze.")

    if not os.path.exists(png_path):
        return abort(f"Freeze PNG missing at {png_path}. Prep render lost.")

    # 2. POST -- THE SACRED ACT ---------------------------------------------
    try:
        with open(bit_path, encoding="utf-8") as f:
            raw = f.read()
        alt_text = vc.markdown_to_alt_text(raw)

        creds = vc.load_bluesky_creds()
        sess = vc.create_session(creds["BLUESKY_HANDLE"], creds["BLUESKY_APP_PASSWORD"])
        token, did = sess["accessJwt"], sess["did"]

        with open(png_path, "rb") as f:
            image_bytes = f.read()
        blob = vc.upload_blob(token, image_bytes)
        post = vc.create_post(token, did, blob, alt_text)
        uri = post.get("uri", "?")
        log(f"POSTED {tag}: {uri}")
    except Exception as e:  # noqa: BLE001
        log(f"POST FAILED: {e}")
        vc.send_mail(f"VerbAItim post ✗ FAILED {tag}",
                     f"The post itself failed: {e}\nCursor NOT advanced; "
                     f"freeze left intact for a manual retry.")
        return 1

    # 3. ADVANCE CURSOR LOCALLY (commit point -- before push) ---------------
    vc.write_cursor(num)
    vc.clear_freeze()
    log(f"cursor -> {num:04d}, freeze cleared")

    # 4. COMMIT + PUSH (best-effort; failure = sync problem, never re-post) --
    push_note = ""
    try:
        git(["add", "bits/.cursor"], 15)
        c = git(["commit", "-m", f"posted {tag}"], 15)
        p = git(["push"], PUSH_TIMEOUT)
        if p.returncode != 0:
            push_note = f"\n\n⚠ push failed (rc={p.returncode}): {p.stderr.strip()}\n" \
                        f"Local cursor is correct; sync manually before laptop edits."
            log(f"WARN push failed: {p.stderr.strip()}")
        else:
            log("committed + pushed cursor")
        _ = c
    except Exception as e:  # noqa: BLE001
        push_note = f"\n\n⚠ commit/push errored: {e}\nLocal cursor is correct."
        log(f"WARN commit/push errored: {e}")

    # 5. HEARTBEAT (always) -------------------------------------------------
    elapsed = time.perf_counter() - t0
    remaining = vc.remaining_count(num)
    vc.send_mail(
        f"VerbAItim ✓ posted {tag}",
        f"{tag} is live ({uri}).\nCursor advanced to {num:04d}. "
        f"{remaining} bits remain.\nPosted in {elapsed:.1f}s.{push_note}",
    )
    log(f"DONE in {elapsed:.1f}s; {remaining} remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
