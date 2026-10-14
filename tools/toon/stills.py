"""Render the 2D style test stills: python tools/toon/stills.py OUT_DIR (needs cairosvg)."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import art, cairosvg
from PIL import Image
out = sys.argv[1]
shots = {
 "wide": ((1080, 2280, 2900), {}),
 "med": ((1080, 1900, 1050), {"mouth": "C", "brow": 0.6}),
 "gesture": ((1080, 2050, 1500), {"mouth": "D", "brow": 1, "l_up": -35, "l_fore": -125, "l_hand": "open", "head": -4}),
}
ims = []
for k, (cam, pose) in shots.items():
    cairosvg.svg2png(bytestring=art.frame(cam, pose).encode(), write_to=f"{out}/{k}.png")
    ims.append(Image.open(f"{out}/{k}.png").convert("RGB").resize((480, 853)))
c = Image.new("RGB", (1440, 853)); [c.paste(im, (i * 480, 0)) for i, im in enumerate(ims)]
c.save(f"{out}/sheet.jpg", quality=90)
