"""Kaggle GPU kernel: Wan 2.2 I2V 14B (GGUF) + lightx2v 4-step LoRA, run headless in ComfyUI.

Pushed by tools/kaggle_run.sh. Reads every shots.json found under /kaggle/input:
    [{"name": "action01", "image": "action_start.png", "prompt": "...", "negative": "...",
      "width": 480, "height": 832, "frames": 81, "seed": 7}, ...]
(image paths are relative to the shots.json folder) and writes, per shot,
/kaggle/working/<name>.mp4 (16 fps) plus timing.json with how long each step took.

Models (all free, Apache-2.0): QuantStack Wan2.2-I2V-A14B GGUF high/low-noise experts,
Comfy-Org repackaged umt5-xxl text encoder, Wan 2.1 VAE and the lightx2v 4-step LoRAs.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

T0 = time.time()
COMFY = Path("/tmp/ComfyUI")
OUT = Path("/kaggle/working")
QUANT = os.environ.get("WAN_QUANT", "Q5_K_M")
timing = {}


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sh(cmd, **kw):
    log("$", cmd)
    subprocess.run(cmd, shell=True, check=True, **kw)


def step(name):
    timing[name] = round(time.time() - T0, 1)
    log("== done:", name)


MODELS = [
    ("QuantStack/Wan2.2-I2V-A14B-GGUF", f"HighNoise/Wan2.2-I2V-A14B-HighNoise-{QUANT}.gguf", "unet"),
    ("QuantStack/Wan2.2-I2V-A14B-GGUF", f"LowNoise/Wan2.2-I2V-A14B-LowNoise-{QUANT}.gguf", "unet"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/vae/wan_2.1_vae.safetensors", "vae"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "loras"),
    ("Comfy-Org/Wan_2.2_ComfyUI_Repackaged", "split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "loras"),
]
NAMES = {f: Path(f).name for _, f, _ in MODELS}

NEGATIVE = ("blurry, low quality, distorted face, deformed hands, extra fingers, extra limbs, "
            "flicker, jitter, morphing, melting, warped body, static frame, text, watermark, subtitles")


def install():
    sh("nvidia-smi; free -g; df -h /tmp /kaggle/working")
    sh(f"git clone -q --depth 1 https://github.com/comfyanonymous/ComfyUI {COMFY}")
    sh(f"git clone -q --depth 1 https://github.com/city96/ComfyUI-GGUF {COMFY}/custom_nodes/ComfyUI-GGUF")
    # Keep Kaggle's CUDA torch; install the rest.
    reqs = [l for l in (COMFY / "requirements.txt").read_text().splitlines()
            if l.strip() and not l.startswith(("torch", "torchvision", "torchaudio"))]
    (COMFY / "req_notorch.txt").write_text("\n".join(reqs))
    sh(f"{sys.executable} -m pip install -q -r {COMFY}/req_notorch.txt gguf hf_transfer")
    step("install")


def download():
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    from huggingface_hub import hf_hub_download

    def get(repo, f, sub):
        p = hf_hub_download(repo, f, local_dir="/tmp/hf")
        dst = COMFY / "models" / sub / Path(f).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(p, dst)
        log("got", dst.name, round(dst.stat().st_size / 1e9, 2), "GB")

    threads = [threading.Thread(target=get, args=m) for m in MODELS]
    [t.start() for t in threads]
    [t.join() for t in threads]
    step("download")


def start_server():
    logf = open("/tmp/comfy.log", "w")
    proc = subprocess.Popen([sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188",
                             "--disable-auto-launch"], cwd=COMFY, stdout=logf, stderr=subprocess.STDOUT)
    for _ in range(300):
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)
            step("server")
            return proc
        except Exception:
            if proc.poll() is not None:
                break
            time.sleep(2)
    print(open("/tmp/comfy.log").read())
    raise SystemExit("ComfyUI did not start")


def workflow(s, image_name):
    seed = s.get("seed", 7)
    sampler = dict(steps=4, cfg=1.0, sampler_name="euler", scheduler="simple", noise_seed=seed,
                   positive=["12", 0], negative=["12", 1])
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": NAMES[MODELS[0][1]]}},
        "2": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": NAMES[MODELS[1][1]]}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": NAMES[MODELS[4][1]], "strength_model": 1.0}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["2", 0], "lora_name": NAMES[MODELS[5][1]], "strength_model": 1.0}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["3", 0], "shift": 5.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["4", 0], "shift": 5.0}},
        "7": {"class_type": "CLIPLoader", "inputs": {"clip_name": NAMES[MODELS[2][1]], "type": "wan"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": s["prompt"]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": s.get("negative", NEGATIVE)}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": NAMES[MODELS[3][1]]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "12": {"class_type": "WanImageToVideo", "inputs": {
            "positive": ["8", 0], "negative": ["9", 0], "vae": ["10", 0], "start_image": ["11", 0],
            "width": s.get("width", 480), "height": s.get("height", 832), "length": s.get("frames", 81), "batch_size": 1}},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {
            **sampler, "model": ["5", 0], "latent_image": ["12", 2], "add_noise": "enable",
            "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable"}},
        "14": {"class_type": "KSamplerAdvanced", "inputs": {
            **sampler, "model": ["6", 0], "latent_image": ["13", 0], "add_noise": "disable",
            "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable"}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["10", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": s["name"]}},
    }


def run_shot(s, base):
    img = base / s["image"]
    shutil.copy(img, COMFY / "input" / img.name)
    req = json.dumps({"prompt": workflow(s, img.name), "client_id": "kaggle"}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:8188/prompt", req, {"Content-Type": "application/json"})))
    pid, t = r["prompt_id"], time.time()
    log("queued", s["name"], pid)
    while True:
        time.sleep(5)
        h = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") != "success":
                print(open("/tmp/comfy.log").read()[-6000:])
                raise SystemExit(f"shot {s['name']} failed: {st}")
            break
        if time.time() - t > 3 * 3600:
            raise SystemExit("timeout")
    frames = sorted((COMFY / "output").glob(f"{s['name']}_*.png"))
    sh(f"ffmpeg -loglevel error -y -framerate 16 -i {COMFY}/output/{s['name']}_%05d_.png "
       f"-c:v libx264 -crf 14 -pix_fmt yuv420p {OUT}/{s['name']}.mp4")
    for i in (0, len(frames) // 2, len(frames) - 1):
        shutil.copy(frames[i], OUT / f"{s['name']}_f{i:03d}.png")
    timing[f"shot_{s['name']}_sec"] = round(time.time() - t, 1)
    step(f"shot {s['name']} ({len(frames)} frames)")


def main():
    shots = []
    for f in glob.glob("/kaggle/input/**/shots.json", recursive=True):
        shots += [(s, Path(f).parent) for s in json.loads(Path(f).read_text())]
    log("shots:", [s["name"] for s, _ in shots])
    install()
    download()
    proc = start_server()
    try:
        for s, base in shots:
            run_shot(s, base)
            (OUT / "timing.json").write_text(json.dumps(timing, indent=1))
    finally:
        shutil.copy("/tmp/comfy.log", OUT / "comfy.log")
        (OUT / "timing.json").write_text(json.dumps(timing, indent=1))
        proc.terminate()
    log("ALL DONE", timing)


main()
