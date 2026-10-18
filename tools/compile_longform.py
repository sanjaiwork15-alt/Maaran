"""Compile a series' finished Shorts into one 16:9 long-form video (Groundnut long-form).

Usage (toon venv):
    python tools/compile_longform.py series/01-groundnut/longform/cuts.json OUT.mp4

cuts.json: hook (new voice lines + Ep video ranges), title card, the kept range(s) of each episode's final mp4
(original picture, voice and nature sound untouched), closing (new voice over the farm view) and end card.
Every 9:16 piece is centred on 1920x1080 over a blurred, darkened copy of itself; joins get 0.08 s audio
fades and a 0.25 s dip between episodes. New voice is mixed with tools/ambience.py like the Shorts (-14 LUFS).
"""
import io
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cairosvg
import numpy as np
import soundfile as sf
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from join_voice import SR, load_trimmed  # noqa: E402

W, H, FPS = 1920, 1080, 25
FIT = (f"split[a][b];[a]scale={W}:-2,crop={W}:{H},boxblur=30:3,eq=brightness=-0.12:saturation=0.8[bg];"
       f"[b]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,setsar=1,fps={FPS},format=yuv420p")
ENC = ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-video_track_timescale", "12800"]
PY = sys.executable


def ff(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def ep_file(base, ep):
    return base.parent / ep / "final" / f"groundnut_{ep}.mp4"


def episode_piece(src, a, b, out, dip_in, dip_out):
    if out.exists():           # cached: the cut list names the piece
        return
    n = round((b - a) * FPS)
    d = n / FPS
    vf = FIT
    if dip_in:
        vf += ",fade=in:st=0:d=0.25"
    if dip_out:
        vf += f",fade=out:st={d - 0.25:.3f}:d=0.25"
    af = f"afade=in:st=0:d=0.08,afade=out:st={d - 0.08:.3f}:d=0.08"
    ff("-ss", f"{a:.3f}", "-i", str(src), "-t", f"{d:.3f}", "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[o]",
       "-map", "[v]", "-map", "[o]", "-frames:v", str(n), *ENC, str(out))


def voice_track(vdir, lines, ids, tmp, length):
    """New voice lines joined like join_voice, mixed over a nature bed, padded to length."""
    L = {l["id"]: l for l in lines}
    parts = [np.zeros(int(0.35 * SR), np.float32)]
    for k in ids:
        parts += [load_trimmed(str(vdir / f"{k}.wav")), np.zeros(int(L[k]["pause_after"] * SR), np.float32)]
    x = np.concatenate(parts)
    x = x / max(1e-6, np.abs(x).max()) * 0.9
    length = max(length, len(x) / SR + 0.4)
    x = np.pad(x, (0, int(length * SR) - len(x)))
    sf.write(tmp / "v.wav", x, SR)
    subprocess.run([PY, str(ROOT / "tools/ambience.py"), str(tmp / "bed.wav"), f"{length + 0.5:.2f}", "--no-rooster"],
                   check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    subprocess.run([PY, str(ROOT / "tools/mix.py"), str(tmp / "v.wav"), str(tmp / "bed.wav"), str(tmp / "mix.wav")],
                   check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return tmp / "mix.wav", length


def card_png(kind, out):
    bg = Image.open(ROOT / "assets/2d/up/05_field_vertical.png").convert("RGB")
    s = W / bg.width
    bg = bg.resize((W, round(bg.height * s)))
    top = round(bg.height * 0.42 - H / 2)
    bg = bg.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(14))
    bg = ImageEnhance.Brightness(bg).enhance(0.62)
    pod = ("M -46,0 C -46,-24 -16,-26 -6,-14 C 2,-24 46,-28 50,0 C 46,28 2,24 -6,14 C -16,26 -46,24 -46,0 Z")
    net = "".join(f'<path d="M {a},-20 C {a + 6},-6 {a + 6},6 {a},20" stroke="#a9834d" stroke-width="3" fill="none"/>'
                  for a in (-34, -20, 10, 26, 40))
    icons = (f'<g transform="translate(-70 0)"><path d="M 0,40 C 0,10 0,-10 0,-30" stroke="#3b2416" stroke-width="12"/>'
             f'<path d="M 0,40 C 0,10 0,-10 0,-30" stroke="#6fae3a" stroke-width="7"/>'
             f'<path d="M 0,-20 C -40,-50 -60,-20 -55,-5 C -35,0 -10,-5 0,-20 Z" fill="#7cc243" stroke="#3b2416" stroke-width="5"/>'
             f'<path d="M 0,-28 C 30,-65 60,-40 58,-22 C 40,-12 12,-14 0,-28 Z" fill="#7cc243" stroke="#3b2416" stroke-width="5"/></g>'
             f'<g transform="translate(70 5) rotate(-20) scale(1.15)"><path d="{pod}" fill="#e3c28a" stroke="#3b2416" stroke-width="5"/>{net}</g>')
    font = "font-family='Inter Display, Inter, DejaVu Sans' text-anchor='middle'"
    if kind == "title":
        body = (f"<g transform='translate({W / 2} 250) scale(1.4)'>{icons}</g>"
                f"<text x='{W / 2}' y='470' {font} font-size='132' font-weight='900' fill='#ffd84a' stroke='#3b2416' "
                f"stroke-width='10' paint-order='stroke' letter-spacing='4'>FROM SEED TO SNACK</text>"
                f"<text x='{W / 2}' y='580' {font} font-size='60' font-weight='700' fill='#ffffff' stroke='#3b2416' "
                f"stroke-width='7' paint-order='stroke'>The Complete Groundnut Farming Journey</text>"
                f"<rect x='{W / 2 - 330}' y='650' width='660' height='92' rx='46' fill='#5c8f2e' stroke='#3b2416' stroke-width='6'/>"
                f"<text x='{W / 2}' y='713' {font} font-size='50' font-weight='800' fill='#ffffff'>Maaran Thatha's Farm</text>")
    else:
        body = (f"<g transform='translate({W / 2} 170) scale(1.2)'>{icons}</g>"
                f"<text x='{W / 2}' y='360' {font} font-size='112' font-weight='900' fill='#ffd84a' stroke='#3b2416' "
                f"stroke-width='10' paint-order='stroke' letter-spacing='3'>FROM SEED TO SNACK</text>"
                f"<rect x='{W / 2 - 600}' y='440' width='1200' height='130' rx='65' fill='#d6332a' stroke='#3b2416' stroke-width='7'/>"
                f"<text x='{W / 2}' y='530' {font} font-size='66' font-weight='800' fill='#ffffff'>Subscribe to Maaran Thatha's Farm</text>"
                f"<text x='{W / 2}' y='700' {font} font-size='60' font-weight='700' fill='#ffffff' stroke='#3b2416' "
                f"stroke-width='7' paint-order='stroke'>More Farming Stories Coming Soon!</text>")
    def outline(m):        # cairosvg ignores paint-order: draw an outline copy under the text
        under = re.sub(r"fill='[^']*'", f"fill='{m[2]}'", m[1])
        return (f"<text {under} stroke='{m[2]}' stroke-width='{m[3]}' stroke-linejoin='round'>{m[4]}</text>"
                f"<text {m[1]}>{m[4]}</text>")
    body = re.sub(r"<text ([^>]*?) stroke='([^']+)' stroke-width='(\d+)' paint-order='stroke'>([^<]*)</text>", outline, body)
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}'>{body}</svg>"
    fg = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
    bg.paste(fg, (0, 0), fg)
    bg.save(out)


def card_piece(kind, d, tmp, out):
    png = tmp / f"{kind}.png"
    card_png(kind, png)
    subprocess.run([PY, str(ROOT / "tools/ambience.py"), str(tmp / f"{kind}_bed.wav"), f"{d + 0.5:.2f}", "--no-rooster"],
                   check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    n = round(d * FPS)
    ff("-loop", "1", "-i", str(png), "-i", str(tmp / f"{kind}_bed.wav"), "-filter_complex",
       f"[0:v]scale={2 * W}:{2 * H},zoompan=z='1+0.04*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS},"
       f"fade=in:st=0:d=0.4,fade=out:st={d - 0.4:.3f}:d=0.4,format=yuv420p[v];"
       f"[1:a]volume=-6dB,afade=in:st=0:d=0.4,afade=out:st={d - 0.5:.3f}:d=0.5[a]",
       "-map", "[v]", "-map", "[a]", "-frames:v", str(n), "-t", f"{d:.3f}", *ENC, str(out))


def vo_piece(cfg, base, lines, tmp, out, still=None):
    """Footage (video only) cut to the new voice line's length; the last range (or still) stretches to fit."""
    vdir = base / "voice_lines"
    rng = cfg["video"]
    total = sum(b - a for _, a, b in rng)
    audio, length = voice_track(vdir, lines, cfg["voice"], tmp, total)
    segs, inp = [], []
    for i, (ep, a, b) in enumerate(rng):
        d = b - a
        if i == len(rng) - 1 and not still:
            d = length - (total - d)
        inp += ["-ss", f"{a:.3f}", "-t", f"{min(d, b - a):.3f}", "-i", str(ep_file(base, ep))]
        pad = f",tpad=stop_mode=clone:stop_duration={max(0, d - (b - a)):.3f}" if d > b - a else ""
        segs.append(f"[{i}:v]{FIT}{pad},trim=duration={d:.3f},setpts=PTS-STARTPTS[s{i}]")
    k = len(rng)
    if still:
        rest = length - total
        inp += ["-stream_loop", "-1", "-i", str(base / still)]
        segs.append(f"[{k}:v]{FIT},trim=duration={rest:.3f},setpts=PTS-STARTPTS,"
                    f"scale={2 * W}:{2 * H},zoompan=z='1.0+0.06*on/{round(rest * FPS)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS}[s{k}]")
        k += 1
    inp += ["-i", str(audio)]
    fc = ";".join(segs) + ";" + "".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0,fade=in:st=0:d=0.3,fade=out:st={length - 0.3:.3f}:d=0.3[v]"
    fc += f";[{k}:a]atrim=duration={length:.3f},afade=out:st={length - 0.3:.3f}:d=0.3[a]"
    ff(*inp, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-frames:v", str(round(length * FPS)), *ENC, str(out))


def main():
    cuts_p, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    base = cuts_p.parent
    cfg = json.loads(cuts_p.read_text())
    lines = json.loads((base / "lines.json").read_text())
    work = base / ".pieces"
    work.mkdir(exist_ok=True)
    pieces = []
    jobs = []
    with ThreadPoolExecutor(4) as ex:
        t = work / "hook"; t.mkdir(exist_ok=True)
        pieces.append(work / "00_hook.mp4"); jobs.append(ex.submit(vo_piece, cfg["hook"], base, lines, t, pieces[-1]))
        pieces.append(work / "01_title.mp4"); jobs.append(ex.submit(card_piece, "title", cfg["title"]["duration"], work, pieces[-1]))
        eps = cfg["episodes"]
        for i, (ep, a, b) in enumerate(eps):
            first = i == 0 or eps[i - 1][0] != ep
            last = i == len(eps) - 1 or eps[i + 1][0] != ep
            pieces.append(work / f"{10 + i:02d}_{ep}_{a:.2f}.mp4")
            jobs.append(ex.submit(episode_piece, ep_file(base, ep), a, b, pieces[-1], first, last))
        t = work / "closing"; t.mkdir(exist_ok=True)
        pieces.append(work / "90_closing.mp4")
        jobs.append(ex.submit(vo_piece, cfg["closing"], base, lines, t, pieces[-1], cfg["closing"].get("still")))
        pieces.append(work / "91_end.mp4"); jobs.append(ex.submit(card_piece, "end", cfg["end"]["duration"], work, pieces[-1]))
        for j in jobs:
            j.result()
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in pieces))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out))
    print("saved", out, round(dur(out), 2), "s")


if __name__ == "__main__":
    main()
