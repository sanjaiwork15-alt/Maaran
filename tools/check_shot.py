"""Automatic first-pass check of an AI shot before assembly: glitches, smudges, drift.

Usage:
    python tools/check_shot.py SHOT.mp4 [SHOT2.mp4 ...] [--out DIR] [--start FRAME.png]

For every clip it writes DIR/<name>_sheet.jpg, a contact sheet to look at (12 evenly spaced frames
plus the frames around any flagged moment, flagged ones outlined red with the suspect area boxed),
and prints a one-line verdict. Checks:
  jump    a frame that changes much more than its neighbours (morph, flash, pop)
  smudge  a blotch of "dirty cream" (darker, yellow-brown) where the start frame had clean shirt or
          veshti, like the Ep 1 intro chest-tap smudge (scored 1.1% of the frame; clean shots < 0.2%)
  drift   most of the start frame's clean cloth no longer clean (outfit redrawn or covered)
For shots where the camera or Thatha moves a lot (walking), smudge/drift are only a rough guide.
It does not count hands: look at the sheet for that (one left, one right, stick in his right hand).
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SW = 240                     # analysis width


def frames(path):
    cap = cv2.VideoCapture(str(path))
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    return out


def small(f):
    h = round(f.shape[0] * SW / f.shape[1])
    return cv2.resize(f, (SW, h), interpolation=cv2.INTER_AREA)


def lab(img):
    L = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    return L[..., 0] * 100 / 255, np.hypot(L[..., 1] - 128, L[..., 2] - 128), L[..., 2] - 128


def cloth_mask(img):
    """Flat cream/white cloth (shirt, veshti) of the start frame, shrunk so small sways stay inside it."""
    l, c, _ = lab(img)
    return ndimage.binary_erosion((l > 89) & (c < 24), iterations=4)


def dirty(img, cloth0):
    """'Dirty cream' where the start frame had clean cloth: darker and more yellow-brown than the cloth,
    which the art's own soft shading never is (tuned on the Ep 1 intro chest-tap smudge)."""
    l, c, b = lab(img)
    return ndimage.binary_opening(cloth0 & (l > 66) & (l <= 88) & (c >= 20) & (b > 8), iterations=1)


def check(path, out_dir, start=None):
    fs = frames(path)
    if not fs:
        return f"{path.name}: could not read"
    sm = [small(f) for f in fs]
    ref = small(np.asarray(Image.open(start).convert("RGB").resize(fs[0].shape[1::-1]))) if start else sm[0]
    cloth0 = cloth_mask(ref)
    area = sm[0].shape[0] * sm[0].shape[1]

    diffs = np.array([np.abs(sm[i].astype(np.int16) - sm[i - 1]).mean() for i in range(1, len(sm))])
    med = np.median(diffs) + 0.5
    jumps = [i + 1 for i, d in enumerate(diffs) if d > 4 * med and d > 6]

    smudges, drift = {}, []
    for i in range(0, len(sm), 2):
        d = dirty(sm[i], cloth0)
        lab_, n = ndimage.label(d)
        if n:
            sizes = ndimage.sum(d, lab_, range(1, n + 1))
            j = int(sizes.argmax())
            if sizes[j] > area * 0.0025:          # Ep 1 smudge: up to 1.1%; clean shots stay under 0.16%
                sl = ndimage.find_objects(lab_)[j]
                smudges[i] = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, sizes[j] / area)
        l, c, _ = lab(sm[i])
        drift.append(1 - ((l > 89) & (c < 24))[cloth0].mean() if cloth0.any() else 0)
    drifting = len(drift) > 4 and np.mean(drift[-3:]) > 0.35       # most of the clean cloth is gone / redrawn

    # contact sheet
    flagged = sorted(set(jumps) | set(smudges))
    pick = sorted(set(np.linspace(0, len(fs) - 1, 12).round().astype(int)) | set(flagged[:12]))
    th = 220
    tw = round(th * fs[0].shape[1] / fs[0].shape[0])
    cols = 8
    rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 16)), "white")
    dr = ImageDraw.Draw(sheet)
    k = tw / SW
    for n, i in enumerate(pick):
        x, y = (n % cols) * tw, (n // cols) * (th + 16)
        sheet.paste(Image.fromarray(fs[i]).resize((tw, th)), (x, y))
        bad = i in flagged
        dr.text((x + 3, y + th + 2), f"{i}{' JUMP' if i in jumps else ''}{' SMUDGE' if i in smudges else ''}",
                fill="red" if bad else "black")
        if bad:
            dr.rectangle([x, y, x + tw - 1, y + th - 1], outline="red", width=3)
        if i in smudges:
            a, b, c, d, _ = smudges[i]
            dr.rectangle([x + a * k, y + b * k, x + c * k, y + d * k], outline="magenta", width=2)
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = out_dir / f"{path.stem}_sheet.jpg"
    sheet.save(sheet_path, quality=88)

    worst = max((v[4] for v in smudges.values()), default=0)
    verdict = "CHECK" if (jumps or smudges or drifting) else "ok"
    return (f"{path.name}: {verdict}  frames={len(fs)}  jumps={jumps[:8]}  "
            f"smudge_frames={len(smudges)} (largest {worst:.1%} of frame)  "
            f"drift={'yes' if drifting else 'no'}  sheet={sheet_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--out", default="")
    ap.add_argument("--start", default="", help="the start frame the clip was made from (better palette)")
    a = ap.parse_args()
    for c in a.clips:
        c = Path(c)
        print(check(c, Path(a.out) if a.out else c.parent / "check", a.start or None), flush=True)


if __name__ == "__main__":
    main()
