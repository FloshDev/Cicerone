"""Genera packaging/icon.icns per Cicerone.

Design:
- Sfondo cream chiaro (#FAFAF7)
- Anello sottile ambrato (#E8B84B) con doppio bordo interno fine
- "C" serif (Georgia Bold) in nero antracite (#2A2418) centrata
- Ombra morbida sotto la C per profondità

Esegui:
    python packaging/generate_icon.py

Output:
    packaging/icon.icns
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUT_ICNS = ROOT / "icon.icns"

CREAM = (250, 250, 247, 255)
AMBER = (232, 184, 75, 255)
AMBER_SOFT = (232, 184, 75, 120)
INK = (42, 36, 24, 255)

SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]

FONT_PATH = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


def _rounded_rect_mask(size: int, radius: int) -> Image.Image:
    """Maschera per squircle macOS-like (rounded rect)."""
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _disegna(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Sfondo cream con rounded rect macOS-style (radius ~22% del lato)
    radius = int(size * 0.22)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=CREAM)

    # Doppio bordo ambrato: anello esterno + linea fine interna
    margine = max(1, int(size * 0.06))
    spess = max(1, int(size * 0.018))
    draw.rounded_rectangle(
        (margine, margine, size - 1 - margine, size - 1 - margine),
        radius=int(radius * 0.78),
        outline=AMBER,
        width=spess,
    )
    margine_int = margine + spess + max(1, int(size * 0.022))
    draw.rounded_rectangle(
        (margine_int, margine_int, size - 1 - margine_int, size - 1 - margine_int),
        radius=int(radius * 0.55),
        outline=AMBER_SOFT,
        width=max(1, int(size * 0.006)),
    )

    # "C" serif al centro
    font_size = int(size * 0.62)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "C"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = (size - tw) // 2 - bbox[0]
    cy = (size - th) // 2 - bbox[1] - int(size * 0.02)

    # Ombra ultra-morbida (solo size >= 64)
    if size >= 64:
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.text(
            (cx + int(size * 0.006), cy + int(size * 0.012)),
            text,
            font=font,
            fill=(0, 0, 0, 38),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 110)))
        img.alpha_composite(shadow)

    draw.text((cx, cy), text, font=font, fill=INK)
    return img


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "Cicerone.iconset"
        iconset.mkdir()
        for name, size in SIZES:
            _disegna(size).save(iconset / name, "PNG")

        # iconutil è builtin macOS
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("iconutil errore:", result.stderr)
            return 1

    print(f"Generato: {OUT_ICNS}  ({OUT_ICNS.stat().st_size // 1024} KB)")

    # Salva anche PNG 1024 per preview
    preview = ROOT / "icon_preview.png"
    _disegna(1024).save(preview, "PNG")
    print(f"Preview:  {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
