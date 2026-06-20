"""Genera packaging/icon.icns da resources/branding/logo.png.

Esegui:
    python packaging/generate_icon.py
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
LOGO = PROJECT_ROOT / "resources" / "branding" / "logo.png"
OUT_ICNS = ROOT / "icon.icns"

# Frazione del canvas occupata dallo squircle. macOS usa una rounded-rect di
# ~824px su 1024 (≈0.80); teniamo 0.82 per un margine trasparente coerente con
# le app native senza far sembrare l'icona troppo piccola.
ICON_SCALE = 0.82

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


def _prepare_icon_master(src: Image.Image, canvas: int = 1024) -> Image.Image:
    """Master 1024 RGBA stile icona macOS: squircle ritagliato sull'area opaca,
    centrato su canvas trasparente a ICON_SCALE (margine trasparente per lato).

    Il logo sorgente ha già lo sfondo trasparente (squircle isolato), quindi
    basta ritagliare al contenuto e applicare il padding nativo."""
    clean = src.convert("RGBA")
    bbox = clean.getbbox()  # area opaca
    if bbox:
        clean = clean.crop(bbox)

    target = int(round(canvas * ICON_SCALE))
    cw, ch = clean.size
    ratio = min(target / cw, target / ch)
    new = (max(1, round(cw * ratio)), max(1, round(ch * ratio)))
    clean = clean.resize(new, Image.LANCZOS)

    master = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    off = ((canvas - new[0]) // 2, (canvas - new[1]) // 2)
    master.paste(clean, off, clean)
    return master


def main() -> int:
    if not LOGO.exists():
        print(f"Manca {LOGO}")
        return 1

    src = _prepare_icon_master(Image.open(LOGO))

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "Cicerone.iconset"
        iconset.mkdir()
        for name, size in SIZES:
            src.resize((size, size), Image.LANCZOS).save(iconset / name, "PNG")

        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("iconutil errore:", result.stderr)
            return 1

    print(f"Generato: {OUT_ICNS}  ({OUT_ICNS.stat().st_size // 1024} KB)")

    preview = ROOT / "icon_preview.png"
    src.resize((1024, 1024), Image.LANCZOS).save(preview, "PNG")
    print(f"Preview:  {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
