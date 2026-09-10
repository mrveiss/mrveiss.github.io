"""Render the social card for this property.

One image serves two purposes, which is why it is 1280x640:

  * this repository's GitHub social preview (Settings -> General), which wants
    exactly 1280x640
  * the site's `og:image`, referenced from index.html and served from /assets/

Both want a 2:1 crop -- `twitter:card` is `summary_large_image`, which crops hard --
so a single asset covers them rather than two that can drift apart. The GitHub
preview half still has to be uploaded by hand: it is a repository *setting*, not a
file GitHub reads from the tree, and there is no REST or GraphQL endpoint for it.
The `og:image` half is a file and needs no upload.

Palette and type are taken from index.html so a pasted link reads as the same
property. That page is the source of truth and NOTHING enforces the match -- if its
tokens change, this file must be updated by hand.

No count, no metric, no badge, deliberately: a number baked into an image nobody
revisits becomes false without anything reporting it, and this is a property whose
subject is measuring honestly.

Fonts are not vendored -- see README.md. This module makes no network call.

Usage:
    python3 assets/make_card.py --fonts ./fonts --out assets
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 640
MARGIN = 88
RULE_Y = 430

BG = "#1e1418"
SUNKEN = "#150d11"
BORDER = "#402c34"
CREAM = "#f1e8de"
MUTED = "#b3a596"
SUBTLE = "#82737a"
ACCENT = "#e2842e"

EYEBROW = "MRVEISS  ·  SELF-HOSTED AGENTIC AI"
LICENCE = "Apache-2.0"

CARD = {
    "out": "social-card.png",
    "title": "Agentic AI ",
    "accent": "you own.",
    "sub": "Runs on your infrastructure — your data, your models.",
    "detail": "voice & chat  ·  browser and computer control  ·  workflows  ·  RBAC  ·  knowledge graph",
    "command": "mrveiss.github.io",
}


def _font(fonts: Path, name: str, size: int) -> ImageFont.FreeTypeFont:
    """Fail loudly on a missing font.

    A substituted face would change the card without changing the code, so the
    card would silently stop matching the page it is supposed to echo.
    """
    path = fonts / f"{name}.ttf"
    if not path.exists():
        raise SystemExit(f"missing font: {path} — see README.md for where to fetch it")
    return ImageFont.truetype(str(path), size)


CONTENT_W = WIDTH - MARGIN * 2


def _fit(draw, text, font, label) -> None:
    """Refuse to render text wider than the content column.

    The first draft overflowed by 77px and the PNG simply ran the subtitle off the
    right edge -- no error, and it looks deliberate at a glance. Clipping is exactly
    the kind of defect that survives review, so it fails here instead.
    """
    width = draw.textlength(text, font=font)
    if width > CONTENT_W:
        raise SystemExit(
            f"{label} is {width:.0f}px wide, {CONTENT_W}px available "
            f"({width - CONTENT_W:.0f}px over) — shorten it or reduce its size:\n  {text}"
        )


def _tracked(draw, xy, text, font, fill, tracking) -> None:
    """Draw letter-spaced text; Pillow has no tracking of its own."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking


def _accent_mark(draw) -> None:
    """The property's favicon disc, bled off the top-right corner."""
    draw.ellipse([WIDTH - 150, -150, WIDTH + 150, 150], fill=ACCENT)
    draw.ellipse([WIDTH - 132, -132, WIDTH + 132, 132], fill=BG)
    draw.ellipse([WIDTH - 96, -96, WIDTH + 96, 96], fill=ACCENT)


def _draw_headline(draw, fonts: Path) -> None:
    _tracked(draw, (MARGIN, 92), EYEBROW, _font(fonts, "JetBrainsMono", 21), SUBTLE, 3.2)

    display = _font(fonts, "Fraunces", 82)
    draw.text((MARGIN, 158), CARD["title"], font=display, fill=CREAM)
    offset = MARGIN + draw.textlength(CARD["title"], font=display)
    draw.text((offset, 158), CARD["accent"], font=display, fill=ACCENT)

    sub = _font(fonts, "Schibsted", 37)
    _fit(draw, CARD["sub"], sub, "sub")
    draw.text((MARGIN, 274), CARD["sub"], font=sub, fill=MUTED)

    detail = _font(fonts, "Schibsted", 23)
    _fit(draw, CARD["detail"], detail, "detail")
    draw.text((MARGIN, 336), CARD["detail"], font=detail, fill=SUBTLE)


def _draw_footer(draw, fonts: Path) -> None:
    """The hairline separates what this is from where to find it."""
    caption = _font(fonts, "JetBrainsMono", 19)
    draw.text(
        (WIDTH - MARGIN - draw.textlength(LICENCE, font=caption), RULE_Y - 30),
        LICENCE,
        font=caption,
        fill=SUBTLE,
    )
    draw.line([MARGIN, RULE_Y, WIDTH - MARGIN, RULE_Y], fill=BORDER, width=2)

    mono = _font(fonts, "JetBrainsMono", 25)
    pad_x, pad_y = 26, 20
    chip_w = draw.textlength(CARD["command"], font=mono) + pad_x * 2
    chip_h = 25 + pad_y * 2 + 6
    top = RULE_Y + 42
    draw.rounded_rectangle(
        [MARGIN, top, MARGIN + chip_w, top + chip_h],
        radius=12,
        fill=SUNKEN,
        outline=BORDER,
        width=2,
    )
    draw.text((MARGIN + pad_x, top + pad_y - 2), CARD["command"], font=mono, fill=CREAM)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the social card.")
    parser.add_argument("--fonts", type=Path, default=Path(__file__).parent / "fonts")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _accent_mark(draw)
    _draw_headline(draw, args.fonts)
    _draw_footer(draw, args.fonts)

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / CARD["out"]
    img.save(dest, "PNG", optimize=True)
    print(f"{dest}  {WIDTH}x{HEIGHT}  {dest.stat().st_size} bytes")


if __name__ == "__main__":
    main()
