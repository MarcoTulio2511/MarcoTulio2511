#!/usr/bin/env python3
"""
prep_photo.py — Step 1 of the ASCII-portrait pipeline.

Takes a regular photo and prepares it for ASCII conversion:
  1. Remove the background with rembg so only the subject remains.
  2. Boost local contrast with CLAHE (contrast-limited adaptive
     histogram equalization) so a flatly-lit face gets real
     highlights and shadows instead of converting to a dark blob.
  3. Composite onto pure white so the background maps to the blank
     end of the ASCII ramp (white -> space).

Usage:
    python scripts/prep_photo.py source-photo.jpg
Writes:
    source-prepped.png (grayscale, same basename, in the same folder)
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

# u2net is the well-tested, lightweight (~176MB) rembg model — plenty for a
# portrait cutout and far cheaper than the newer, much heavier default model.
_SESSION = new_session("u2net")


def prep_photo(src_path: str) -> str:
    src = Path(src_path)
    out_path = src.with_name(f"{src.stem}-prepped.png")

    # 1. Remove background -> RGBA with transparent background
    with open(src, "rb") as f:
        input_bytes = f.read()
    result_bytes = remove(input_bytes, session=_SESSION)

    rgba = Image.open(__import__("io").BytesIO(result_bytes)).convert("RGBA")

    # Composite onto pure white immediately so edge pixels don't carry
    # semi-transparent background color into the subject.
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, rgba).convert("RGB")

    # 2. Boost local contrast with CLAHE (operates on grayscale / L channel)
    gray = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Re-mask: anywhere rembg said "background", force back to pure white
    # (CLAHE can pull slight texture out of what should be blank space).
    alpha = np.array(rgba)[:, :, 3]
    enhanced = np.where(alpha < 16, 255, enhanced).astype(np.uint8)

    out_img = Image.fromarray(enhanced, mode="L")
    out_img.save(out_path)
    print(f"wrote {out_path} ({out_img.size[0]}x{out_img.size[1]}, grayscale)")
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/prep_photo.py <source-photo>")
        sys.exit(1)
    prep_photo(sys.argv[1])
