#!/usr/bin/env python3
"""
VerbAItim shared core.

Single source of truth for the risky, reused logic: credential loading,
cursor read/write, next-bit resolution, freeze-marker contract, Resend
mail, and markdown->alt-text. Both prep.py (T-30) and post.py (2:14)
import from here so there is exactly one copy of each dangerous thing.

NOTHING in here posts, pulls, or pushes on import -- it's pure helpers.

CONTENT IS NOT THIS MODULE'S JOB. No UI-artifact stripping, no redaction,
no cleaning. Cleaning and the funny/safety calls happen at clip time in a
control-room session. Everything here renders/handles bits AS-IS.
"""

import os
import re
import json
import glob
from datetime import datetime, timezone
from urllib import request as urlreq
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BITS_DIR = os.path.join(REPO, "bits")
CURSOR_PATH = os.path.join(BITS_DIR, ".cursor")
RENDER_DIR = os.path.join(REPO, "render_output")
FREEZE_PATH = os.path.join(RENDER_DIR, ".freeze")
BSKY_CRED_PATH = os.path.join(HERE, ".bluesky_credentials")
RESEND_CRED_PATH = os.path.join(HERE, ".resend_credentials")

PDS_HOST = "https://bsky.social"
RESEND_URL = "https://api.resend.com/emails"

FREEZE_MAX_AGE_SECONDS = 35 * 60
LOW_INVENTORY_THRESHOLD = 5


def _load_kv(path, required):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing credentials file: {path}")
    creds = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    missing = [k for k in required if k not in creds or not creds[k]]
    if missing:
        raise ValueError(f"{os.path.basename(path)} missing keys: {missing}")
    return creds


def load_bluesky_creds():
    return _load_kv(BSKY_CRED_PATH, ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"))


def load_resend_creds():
    return _load_kv(RESEND_CRED_PATH, ("RESEND_API_KEY", "MAIL_TO", "MAIL_FROM"))


def read_cursor():
    if not os.path.exists(CURSOR_PATH):
        return 0
    with open(CURSOR_PATH, encoding="utf-8") as f:
        content = f.read().strip()
    return int(content) if content else 0


def write_cursor(n):
    with open(CURSOR_PATH, "w", encoding="utf-8") as f:
        f.write(f"{n:04d}\n")


def all_bit_numbers():
    nums = []
    for path in glob.glob(os.path.join(BITS_DIR, "[0-9][0-9][0-9][0-9]-*.md")):
        nums.append(int(os.path.basename(path)[:4]))
    return sorted(nums)


def next_bit(cursor):
    expect = cursor + 1
    hit = glob.glob(os.path.join(BITS_DIR, f"{expect:04d}-*.md"))
    if hit:
        return expect, hit[0]
    for num in all_bit_numbers():
        if num > cursor:
            path = glob.glob(os.path.join(BITS_DIR, f"{num:04d}-*.md"))
            if path:
                return num, path[0]
    return None, None


def remaining_count(cursor):
    return sum(1 for n in all_bit_numbers() if n > cursor)


def markdown_to_alt_text(raw):
    """Screen-reader alt text: strip markdown styling, keep speaker labels
    and line breaks. Renders AS-IS -- no content cleaning (that's Dan's job
    at clip time, not the automation's)."""
    text = raw.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\*\*(Dan|Claude):\*\*\s*", r"\1: ", text, flags=re.MULTILINE)
    text = re.sub(r"\n\*\*(Dan|Claude):\*\*\s*", r"\n\n\1: ", text)
    return text.strip()


def write_freeze(num, bit_path, png_path):
    os.makedirs(RENDER_DIR, exist_ok=True)
    marker = {
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "num": num,
        "tag": f"{num:04d}",
        "bit_path": bit_path,
        "png_path": png_path,
    }
    with open(FREEZE_PATH, "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2)
    return marker


def read_freeze():
    if not os.path.exists(FREEZE_PATH):
        return None
    with open(FREEZE_PATH, encoding="utf-8") as f:
        return json.load(f)


def freeze_age_seconds(marker):
    written = datetime.fromisoformat(marker["written_utc"])
    return (datetime.now(timezone.utc) - written).total_seconds()


def clear_freeze():
    if os.path.exists(FREEZE_PATH):
        os.remove(FREEZE_PATH)


def send_mail(subject, body, creds=None):
    """Send heartbeat/alarm via Resend. Returns (ok, detail). Never raises."""
    try:
        creds = creds or load_resend_creds()
    except Exception as e:  # noqa: BLE001
        return False, f"resend creds unavailable: {e}"
    payload = json.dumps({
        "from": f"VerbAItim <{creds['MAIL_FROM']}>",
        "to": [creds["MAIL_TO"]],
        "subject": subject,
        "text": body,
    }).encode()
    req = urlreq.Request(
        RESEND_URL, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {creds['RESEND_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "VerbAItim/1.0 (+https://bsky.app/profile/readverbaitim.bsky.social)",
        },
    )
    try:
        with urlreq.urlopen(req, timeout=30) as resp:
            body_resp = json.loads(resp.read())
            return True, body_resp.get("id", "sent")
    except HTTPError as e:
        return False, f"resend HTTP {e.code}: {e.read().decode(errors='replace')}"
    except (URLError, OSError) as e:
        return False, f"resend network error: {e}"


def bsky_request(path, token=None, json_body=None, raw_body=None,
                 content_type=None, timeout=30):
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
    with urlreq.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


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


def preflight_bluesky():
    """Auth-only check: prove the app password still works. Returns (ok, detail)."""
    try:
        creds = load_bluesky_creds()
        sess = create_session(creds["BLUESKY_HANDLE"], creds["BLUESKY_APP_PASSWORD"])
        return True, sess.get("did", "ok")
    except Exception as e:  # noqa: BLE001
        return False, str(e)
