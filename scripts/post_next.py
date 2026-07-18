#!/usr/bin/env python3
"""
VerbAItim Bluesky poster.

Posts exactly one bit per run, in strict numeric order, per bits/.cursor
(plain text file holding the last-posted bit number -- e.g. "0015" means
0016 is next). Meant to be triggered on a daily cadence (one scheduled-task
run = one post), not run in a loop.

Steps:
  1. Read bits/.cursor, find the next bit file in bits/ by number.
  2. Render it via render_bit.py if not already rendered into render_output/.
  3. Auth to Bluesky with an app password (never the main account password).
  4. Upload the image blob, create the post record with alt text.
  5. Advance bits/.cursor. Caller (see post_and_commit.sh) commits + pushes.

Credentials: scripts/.bluesky_credentials, KEY=VALUE per line, gitignored,
never committed:
    BLUESKY_HANDLE=yourhandle.bsky.social
    BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
Create an app password at https://bsky.app/settings/app-passwords --
never use the real account password here.

Usage:
    python3 post_next.py            # post the next bit for real
    python3 post_next.py --dry-run  # render + build the request, don't post
"""

import json
import os
import re
import sys
import glob
import argparse
from datetime import datetime, timezone
from urllib import request as urlreq
from urllib.error import HTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)  # scripts/ -> repo root
BITS_DIR = os.path.join(REPO, "bits")
CURSOR_PATH = os.path.join(BITS_DIR, ".cursor")
CRED_PATH = os.path.join(HERE, ".bluesky_credentials")
RENDER_DIR = os.path.join(REPO, "render_output")

sys.path.insert(0, HERE)
import render_bit  # noqa: E402

PDS_HOST = "https://bsky.social"


def load_credentials():
    if not os.path.exists(CRED_PATH):
        sys.exit(
            f"No credentials file at {CRED_PATH}.\n"
            "Create it (KEY=VALUE per line):\n"
            "  BLUESKY_HANDLE=yourhandle.bsky.social\n"
            "  BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx\n"
            "Generate an app password at https://bsky.app/settings/app-passwords "
            "-- never your real account password."
        )
    creds = {}
    with open(CRED_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    missing = [k for k in ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD") if k not in creds]
    if missing:
        sys.exit(f"Missing keys in {CRED_PATH}: {missing}")
    return creds


def read_cursor():
    if not os.path.exists(CURSOR_PATH):
        return 0
    with open(CURSOR_PATH) as f:
        content = f.read().strip()
    return int(content) if content else 0


def write_cursor(n):
    with open(CURSOR_PATH, "w") as f:
        f.write(f"{n:04d}\n")


def next_bit_path(cursor):
    candidates = sorted(glob.glob(os.path.join(BITS_DIR, "[0-9][0-9][0-9][0-9]-*.md")))
    for path in candidates:
        num = int(os.path.basename(path)[:4])
        if num > cursor:
            return num, path
    return None, None


def markdown_to_alt_text(raw):
    """Plain-text transcript for the image's alt attribute: strip markdown
    styling, keep speaker labels and line breaks readable to a screen reader."""
    text = raw.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\*\*(Dan|Claude):\*\*\s*", r"\1: ", text, flags=re.MULTILINE)
    text = re.sub(r"\n\*\*(Dan|Claude):\*\*\s*", r"\n\n\1: ", text)
    return text.strip()


def bsky_request(path, token=None, json_body=None, raw_body=None, content_type=None):
    url = f"{PDS_HOST}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    req = urlreq.Request(url, data=data, headers=headers, method="POST")
    try:
        with urlreq.urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"Bluesky API error {e.code} on {path}: {body}")


def create_session(handle, app_password):
    return bsky_request(
        "/xrpc/com.atproto.server.createSession",
        json_body={"identifier": handle, "password": app_password},
    )


def upload_blob(token, image_bytes):
    resp = bsky_request(
        "/xrpc/com.atproto.repo.uploadBlob",
        token=token, raw_body=image_bytes, content_type="image/png",
    )
    return resp["blob"]


def create_post(token, did, blob, alt_text):
    record = {
        "$type": "app.bsky.feed.post",
        "text": "",
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [{"image": blob, "alt": alt_text}],
        },
    }
    return bsky_request(
        "/xrpc/com.atproto.repo.createRecord",
        token=token,
        json_body={"repo": did, "collection": "app.bsky.feed.post", "record": record},
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="render + build request, skip the actual post")
    args = ap.parse_args()

    cursor = read_cursor()
    num, bit_path = next_bit_path(cursor)
    if bit_path is None:
        print(f"Nothing to post -- cursor is at {cursor:04d} and no newer bits exist.")
        return

    os.makedirs(RENDER_DIR, exist_ok=True)
    tag = f"{num:04d}"
    png_path = os.path.join(RENDER_DIR, f"{tag}.png")
    render_bit.render(bit_path, png_path, tag=tag)

    with open(bit_path, encoding="utf-8") as f:
        raw = f.read()
    alt_text = markdown_to_alt_text(raw)

    print(f"Next bit: {tag} ({os.path.basename(bit_path)})")
    print(f"Rendered: {png_path}")
    print(f"Alt text ({len(alt_text)} chars): {alt_text[:120]}...")

    if args.dry_run:
        print("--dry-run: not posting, not advancing cursor.")
        return

    creds = load_credentials()
    session = create_session(creds["BLUESKY_HANDLE"], creds["BLUESKY_APP_PASSWORD"])
    token, did = session["accessJwt"], session["did"]

    with open(png_path, "rb") as f:
        image_bytes = f.read()
    blob = upload_blob(token, image_bytes)
    post = create_post(token, did, blob, alt_text)

    write_cursor(num)
    print(f"Posted {tag}: {post.get('uri')}")
    print(f"Cursor advanced to {num:04d}.")


if __name__ == "__main__":
    main()
