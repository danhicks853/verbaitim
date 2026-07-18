#!/usr/bin/env python3
"""
VerbAItim bit renderer.

Reads a bits/NNNN-slug.md file (our "**Dan:** ... **Claude:** ..." dialogue
format) and renders it as a PNG post card matching the approved mockup:
dark card, right-aligned bubble for Dan's lines, plain serif text for
Claude's lines, four-digit tag bottom-right. No timestamps/icons (tested
and rejected as "reads fake").

No browser dependency on purpose -- Pillow + bundled fonts, so this runs
the same way in any fresh sandbox without needing a ~300MB headless-Chromium
install. Supports the narrow markdown vocabulary actually used in bits/:
**bold**, *italic*, `code`, "- " bullets, and a "*(aside)*" meta line.

Known limitation: no color-emoji font is bundled yet, so emoji are stripped
rather than rendered as tofu boxes. Revisit if/when a font file is sourced.

Usage:
    python3 render_bit.py path/to/bits/0015-grandpa-c-pants.md output/0015.png
"""

import re
import sys
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

CANVAS_W = 1080
PAD = 56
CARD_PAD = 44
BG_CARD = (25, 26, 30)
BUBBLE_BG = (43, 44, 49)
BUBBLE_TEXT = (242, 242, 240)
CLAUDE_TEXT = (233, 233, 231)
META_TEXT = (130, 130, 138)
TAG_TEXT = (85, 85, 92)
CODE_BG = (52, 53, 58)

BUBBLE_SIZE = 30
CLAUDE_SIZE = 32
META_SIZE = 22
TAG_SIZE = 22
LINE_GAP = 1.5

FONTS = {
    ("sans", False, False): os.path.join(FONT_DIR, "LiberationSans-Regular.ttf"),
    ("sans", True, False): os.path.join(FONT_DIR, "LiberationSans-Bold.ttf"),
    ("sans", False, True): os.path.join(FONT_DIR, "LiberationSans-Italic.ttf"),
    ("sans", True, True): os.path.join(FONT_DIR, "LiberationSans-Bold.ttf"),
    ("serif", False, False): os.path.join(FONT_DIR, "DejaVuSerif.ttf"),
    ("serif", True, False): os.path.join(FONT_DIR, "DejaVuSerif-Bold.ttf"),
    ("serif", False, True): os.path.join(FONT_DIR, "DejaVuSerif-Italic.ttf"),
    ("serif", True, True): os.path.join(FONT_DIR, "DejaVuSerif-BoldItalic.ttf"),
    ("mono", False, False): os.path.join(FONT_DIR, "DejaVuSansMono.ttf"),
}

_font_cache = {}


def get_font(family, size, bold=False, italic=False):
    key = (family, size, bold, italic)
    if key not in _font_cache:
        path = FONTS.get((family, bold, italic), FONTS[(family, False, False)])
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def strip_emoji(text):
    return re.sub(
        "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+",
        "",
        text,
    )


TURN_RE = re.compile(r"^\*\*(Dan|Claude):\*\*\s*", re.MULTILINE)


def parse_turns(raw):
    raw = raw.strip()
    turns = []
    matches = list(TURN_RE.finditer(raw))
    if not matches:
        return turns
    for i, m in enumerate(matches):
        speaker = m.group(1).lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        text = raw[start:end].strip()
        turns.append({"speaker": speaker, "text": text})
    return turns


INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`.+?`)")


def parse_inline(line):
    runs = []
    for chunk in INLINE_RE.split(line):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**"):
            runs.append((chunk[2:-2], True, False, False))
        elif chunk.startswith("*") and chunk.endswith("*"):
            runs.append((chunk[1:-1], False, True, False))
        elif chunk.startswith("`") and chunk.endswith("`"):
            runs.append((chunk[1:-1], False, False, True))
        else:
            runs.append((chunk, False, False, False))
    return runs


def split_blocks(text):
    blocks = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = para.strip()
        if not para:
            continue
        lines = [l.strip() for l in para.split("\n") if l.strip()]
        for line in lines:
            if line.startswith("- "):
                blocks.append(("bullet", line[2:].strip()))
            else:
                blocks.append(("para", line))
    return blocks


def wrap_runs(runs, family, size, color, max_width, draw, bold_all=False):
    words = []
    for text, bold, italic, code in runs:
        for w in text.split(" "):
            if w == "":
                continue
            # Glue pure-punctuation tokens onto the previous word instead of
            # inserting a space -- happens when a styled run (bold/italic/code)
            # ends right where trailing punctuation begins in the source,
            # e.g. "*safety*." parses as an italic run "safety" immediately
            # followed by a plain run ".", with no space in between.
            if words and re.match(r"^[.,!?;:)\]}’'\u201d]+$", w):
                prev_w, prev_b, prev_i, prev_c = words[-1]
                words[-1] = (prev_w + w, prev_b, prev_i, prev_c)
            else:
                words.append((w, bold or bold_all, italic, code))

    lines = []
    current = []
    current_width = 0
    space_w = draw.textlength(" ", font=get_font(family, size))

    for w, bold, italic, code in words:
        fam = "mono" if code else family
        fsize = int(size * 0.88) if code else size
        font = get_font(fam, fsize, bold, italic)
        w_width = draw.textlength(w, font=font)
        extra = space_w if current else 0
        if current and current_width + extra + w_width > max_width:
            lines.append(current)
            current = []
            current_width = 0
            extra = 0
        current.append((w, font, color, code))
        current_width += extra + w_width
    if current:
        lines.append(current)
    return lines


def render(bit_path, out_path, tag=None):
    with open(bit_path, encoding="utf-8") as f:
        raw = f.read()

    raw = strip_emoji(raw)
    turns = parse_turns(raw)
    if not turns:
        raise ValueError(f"No turns found in {bit_path}")

    if tag is None:
        base = os.path.basename(bit_path)
        m = re.match(r"(\d{4})", base)
        tag = m.group(1) if m else "0000"

    card_w = CANVAS_W - 2 * PAD
    content_w = card_w - 2 * CARD_PAD
    bubble_max_w = int(content_w * 0.82)

    probe = Image.new("RGB", (10, 10))
    pd = ImageDraw.Draw(probe)

    laid_out = []
    y_cursor = CARD_PAD

    for turn in turns:
        speaker = turn["speaker"]
        blocks = split_blocks(turn["text"])

        if speaker == "dan":
            for kind, line in blocks:
                runs = parse_inline(line)
                lines = wrap_runs(runs, "sans", BUBBLE_SIZE, BUBBLE_TEXT, bubble_max_w - 28, pd)
                block_h = int(len(lines) * BUBBLE_SIZE * LINE_GAP)
                laid_out.append({"type": "bubble", "lines": lines, "h": block_h})
                y_cursor += block_h
            y_cursor += 18
        elif speaker == "claude":
            for kind, line in blocks:
                runs = parse_inline(line)
                size = CLAUDE_SIZE
                indent = 34 if kind == "bullet" else 0
                lines = wrap_runs(runs, "serif", size, CLAUDE_TEXT, content_w - indent, pd)
                block_h = int(len(lines) * size * LINE_GAP)
                laid_out.append({
                    "type": "claude_bullet" if kind == "bullet" else "claude_para",
                    "lines": lines, "h": block_h, "indent": indent,
                })
                y_cursor += block_h + 10
            y_cursor += 10

    y_cursor += 30
    canvas_h = y_cursor + PAD
    img = Image.new("RGB", (CANVAS_W, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [PAD - 20, PAD - 20, CANVAS_W - PAD + 20, canvas_h - PAD + 20],
        radius=16, fill=BG_CARD,
    )

    cy = PAD + 24
    for block in laid_out:
        if block["type"] == "bubble":
            lines = block["lines"]
            line_h = BUBBLE_SIZE * LINE_GAP
            text_block_w = max(
                (sum(draw.textlength(w, font=fnt) for w, fnt, c, code in ln)
                 + draw.textlength(" ", font=get_font("sans", BUBBLE_SIZE)) * max(0, len(ln) - 1))
                for ln in lines
            ) if lines else 0
            bubble_w = min(bubble_max_w, text_block_w + 28)
            bubble_h = int(len(lines) * line_h) + 20
            bx1 = CANVAS_W - PAD - CARD_PAD
            bx0 = bx1 - bubble_w
            by0 = cy - 10
            by1 = by0 + bubble_h
            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=BUBBLE_BG)
            ly = by0 + 10
            for ln in lines:
                lw = sum(draw.textlength(w, font=fnt) for w, fnt, c, code in ln)
                lw += draw.textlength(" ", font=get_font("sans", BUBBLE_SIZE)) * max(0, len(ln) - 1)
                lx = bx1 - 14 - lw
                for w, fnt, c, code in ln:
                    draw.text((lx, ly), w, font=fnt, fill=c)
                    lx += draw.textlength(w, font=fnt) + draw.textlength(" ", font=get_font("sans", BUBBLE_SIZE))
                ly += line_h
            cy += bubble_h + 4

        elif block["type"] in ("claude_para", "claude_bullet"):
            lines = block["lines"]
            size = CLAUDE_SIZE
            line_h = size * LINE_GAP
            x0 = PAD + CARD_PAD + block["indent"]
            if block["type"] == "claude_bullet":
                draw.ellipse(
                    [PAD + CARD_PAD + 6, cy + line_h / 2 - 4, PAD + CARD_PAD + 14, cy + line_h / 2 + 4],
                    fill=CLAUDE_TEXT,
                )
            ly = cy
            for ln in lines:
                lx = x0
                for w, fnt, c, code in ln:
                    if code:
                        cw = draw.textlength(w, font=fnt)
                        draw.rounded_rectangle([lx - 4, ly + 2, lx + cw + 4, ly + line_h - 6], radius=5, fill=CODE_BG)
                    draw.text((lx, ly), w, font=fnt, fill=c)
                    lx += draw.textlength(w, font=fnt) + draw.textlength(" ", font=get_font("serif", size))
                ly += line_h
            cy += int(len(lines) * line_h) + 10

    tag_font = get_font("sans", TAG_SIZE)
    tw = draw.textlength(tag, font=tag_font)
    draw.text((CANVAS_W - PAD - CARD_PAD - tw, canvas_h - PAD - 10), tag, font=tag_font, fill=TAG_TEXT)

    img.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: render_bit.py <bit.md> <output.png>")
        sys.exit(1)
    out = render(sys.argv[1], sys.argv[2])
    print(f"wrote {out}")
