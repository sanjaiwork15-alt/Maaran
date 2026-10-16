"""Kaggle GPU kernel: run Maaran Thatha video jobs in headless ComfyUI.

Pushed by tools/kaggle_run.sh. Reads every jobs.json found under /kaggle/input. Each job:
    {"name": "talk01", "type": "s2v", ...}
Paths in a job ("image", "audio") are relative to the jobs.json folder.

Job types (all models free, Apache-2.0, 4-step Lightning/lightx2v LoRAs):
  qwen_edit  Qwen-Image-Edit-2511 redraws the locked reference into a scene (start frames).
             {"image", "prompt", "width", "height", "seeds": [..]} -> <name>_s<seed>.png
  i2v        Wan 2.2 I2V 14B animates a start frame.
             {"image", "prompt", "width", "height", "frames": 81, "seed"} -> <name>.mp4 (16 fps)
  s2v        Wan 2.2 S2V 14B makes Thatha talk from his voice, in 77-frame chunks.
             {"image", "audio", "prompt", "width", "height", "chunks": 2, "seed"} -> <name>.mp4 (16 fps, silent)
  "upscale": true on an i2v/s2v job also writes <name>_up.mp4: every frame through Real-ESRGAN x4plus
             on the second T4 (in the background, while the next job runs), scaled to 1088x1920.

Outputs go to /kaggle/working. Each output is also printed into the run log as base64
(between "@@FILE" and "@@END" lines), because Kaggle's output-file host may not be
reachable from where we fetch results; tools/kaggle_run.sh decodes them.
"""
import base64
import glob
import hashlib
import json
import os
import re
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
timing = {}
EMIT_LOCK = threading.Lock()     # background upscales emit too; keep each file's lines together
REEMITS = []

WAN = "Comfy-Org/Wan_2.2_ComfyUI_Repackaged"
MODELS = {  # key: (repo, file in repo, ComfyUI models folder)
    "wan_i2v_high": ("QuantStack/Wan2.2-I2V-A14B-GGUF", "HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf", "unet"),
    "wan_i2v_low": ("QuantStack/Wan2.2-I2V-A14B-GGUF", "LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf", "unet"),
    "wan_i2v_lora_high": (WAN, "split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "loras"),
    "wan_i2v_lora_low": (WAN, "split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "loras"),
    "wan_s2v": ("QuantStack/Wan2.2-S2V-14B-GGUF", "Wan2.2-S2V-14B-Q4_K_M.gguf", "unet"),
    "wan_s2v_lora": (WAN, "split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "loras"),
    "wav2vec2": (WAN, "split_files/audio_encoders/wav2vec2_large_english_fp16.safetensors", "audio_encoders"),
    "umt5": (WAN, "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders"),
    "wan_vae": (WAN, "split_files/vae/wan_2.1_vae.safetensors", "vae"),
    "qwen_edit": ("unsloth/Qwen-Image-Edit-2511-GGUF", "qwen-image-edit-2511-Q4_K_M.gguf", "unet"),
    "qwen_lora": ("lightx2v/Qwen-Image-Edit-2511-Lightning", "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", "loras"),
    "qwen_vl": ("Comfy-Org/Qwen-Image_ComfyUI", "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors", "text_encoders"),
    "qwen_vae": ("Comfy-Org/Qwen-Image_ComfyUI", "split_files/vae/qwen_image_vae.safetensors", "vae"),
    "esrgan": ("Comfy-Org/Real-ESRGAN_repackaged", "RealESRGAN_x4plus.safetensors", "upscale_models"),
}
NEEDS = {
    "qwen_edit": ["qwen_edit", "qwen_lora", "qwen_vl", "qwen_vae"],
    "i2v": ["wan_i2v_high", "wan_i2v_low", "wan_i2v_lora_high", "wan_i2v_lora_low", "umt5", "wan_vae"],
    "s2v": ["wan_s2v", "wan_s2v_lora", "wav2vec2", "umt5", "wan_vae"],
}
NEGATIVE = ("blurry, low quality, distorted face, deformed hands, extra fingers, extra limbs, "
            "flicker, jitter, morphing, melting, warped body, text, watermark, subtitles")


def M(key):
    return Path(MODELS[key][1]).name


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sh(cmd, **kw):
    log("$", cmd)
    subprocess.run(cmd, shell=True, check=True, **kw)


def step(name):
    timing[name] = round(time.time() - T0, 1)
    log("== done:", name)


def emit(path, again=True):
    """Print a file into the log as base64 so it can be fetched through the logs API."""
    data = Path(path).read_bytes()
    b = base64.b64encode(data).decode()
    with EMIT_LOCK:
        _emit(path, data, b)
    if again:                       # more copies 2 and 5 min later: the log stream drops minutes at a time
        for delay in (120, 300):
            t = threading.Timer(delay, emit, args=(path, False))
            t.start()
            REEMITS.append(t)


def _emit(path, data, b):
    print(f"@@FILE {Path(path).name} {len(data)} {hashlib.sha256(data).hexdigest()}", flush=True)
    for i in range(0, len(b), 8000):
        print("@@B " + b[i:i + 8000], flush=True)
    print("@@END", flush=True)


# ---------------------------------------------------------------- setup

def install():
    if subprocess.run("nvidia-smi", shell=True).returncode:
        raise SystemExit("No GPU attached: this machine_shape is not available to the account")
    sh("free -g; df -h /tmp")
    sh(f"git clone -q --depth 1 https://github.com/comfyanonymous/ComfyUI {COMFY}")
    sh(f"git clone -q --depth 1 https://github.com/city96/ComfyUI-GGUF {COMFY}/custom_nodes/ComfyUI-GGUF")
    # Keep Kaggle's CUDA torch; install the rest.
    reqs = [l for l in (COMFY / "requirements.txt").read_text().splitlines()
            if l.strip() and re.split(r"[<>=~!\[ ;]", l.strip())[0] not in ("torch", "torchvision", "torchaudio")]
    (COMFY / "req_notorch.txt").write_text("\n".join(reqs))
    sh(f"{sys.executable} -m pip install -q -r {COMFY}/req_notorch.txt gguf")
    step("install")


def download(keys):
    from huggingface_hub import hf_hub_download

    def get(key):
        repo, f, sub = MODELS[key]
        p = hf_hub_download(repo, f, local_dir="/tmp/hf")
        dst = COMFY / "models" / sub / Path(f).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(p, dst)
        log("got", dst.name, round(dst.stat().st_size / 1e9, 2), "GB")

    threads = [threading.Thread(target=get, args=(k,)) for k in keys]
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


def run_graph(name, graph):
    req = json.dumps({"prompt": graph, "client_id": "kaggle"}).encode()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:8188/prompt", req, {"Content-Type": "application/json"})))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{name}: workflow rejected: {e.read().decode()[:3000]}")
    pid, t = r["prompt_id"], time.time()
    log("queued", name, pid)
    while True:
        time.sleep(5)
        h = json.load(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}"))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") != "success":
                print(open("/tmp/comfy.log").read()[-6000:])
                raise SystemExit(f"{name} failed: {st}")
            break
        if time.time() - t > 4 * 3600:
            raise SystemExit("timeout")
    timing[f"{name}_sec"] = round(time.time() - t, 1)


def stage(path):
    if not Path(path).exists():          # an image made earlier in this same run
        path = OUT / Path(path).name
    shutil.copy(path, COMFY / "input" / Path(path).name)
    return Path(path).name


def to_mp4(prefix, out):
    sh(f"ffmpeg -loglevel error -y -framerate 16 -i {COMFY}/output/{prefix}_%05d_.png "
       f"-c:v libx264 -crf 16 -pix_fmt yuv420p {out}")


UPSCALERS = []


def upscale_frames(prefix, out, size=(1088, 1920)):
    """Real-ESRGAN x4plus on every frame (fp16, last GPU), resized to `size`, piped to ffmpeg."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from spandrel import ModelLoader
    dev = f"cuda:{torch.cuda.device_count() - 1}"
    model = ModelLoader().load_from_file(str(COMFY / "models/upscale_models" / M("esrgan"))).model.eval().half().to(dev)
    frames = sorted((COMFY / "output").glob(f"{prefix}_*.png"))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{size[0]}x{size[1]}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "17",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    with torch.inference_mode():
        for f in frames:
            x = torch.from_numpy(np.asarray(Image.open(f).convert("RGB"))).to(dev).permute(2, 0, 1)[None].half() / 255
            y = model(x).float()
            y = F.interpolate(y, size=(size[1], size[0]), mode="bicubic", antialias=True, align_corners=False)
            enc.stdin.write((y[0].clamp(0, 1).permute(1, 2, 0) * 255).round().byte().cpu().numpy().tobytes())
    enc.stdin.close()
    enc.wait()
    del model
    torch.cuda.empty_cache()
    log("upscaled", out.name, len(frames), "frames")
    emit(out)


def finish_video(job):
    """Write <name>.mp4, then (optionally) the upscaled copy in the background."""
    to_mp4(job["name"], OUT / f"{job['name']}.mp4")
    emit(OUT / f"{job['name']}.mp4")
    if job.get("upscale"):
        prev = UPSCALERS[-1] if UPSCALERS else None

        def run():
            if prev:
                prev.join()          # one upscale at a time on the spare GPU
            try:
                upscale_frames(job["name"], OUT / f"{job['name']}_up.mp4")
            except Exception as e:
                log("upscale failed:", job["name"], repr(e))
        t = threading.Thread(target=run)
        t.start()
        UPSCALERS.append(t)


# ---------------------------------------------------------------- jobs

def qwen_edit(job, base):
    img = stage(base / job["image"])
    for seed in job.get("seeds", [7]):
        g = {
            "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": M("qwen_edit")}},
            "2": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
            "3": {"class_type": "CFGNorm", "inputs": {"model": ["2", 0], "strength": 1.0}},
            "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["3", 0], "lora_name": M("qwen_lora"), "strength_model": 1.0}},
            "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": M("qwen_vl"), "type": "qwen_image"}},
            "6": {"class_type": "VAELoader", "inputs": {"vae_name": M("qwen_vae")}},
            "7": {"class_type": "LoadImage", "inputs": {"image": img}},
            "8": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["7", 0]}},
            "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["5", 0], "vae": ["6", 0], "image1": ["8", 0], "prompt": job["prompt"]}},
            "10": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["5", 0], "vae": ["6", 0], "image1": ["8", 0], "prompt": ""}},
            "11": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["9", 0], "reference_latents_method": "index_timestep_zero"}},
            "12": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["10", 0], "reference_latents_method": "index_timestep_zero"}},
            "13": {"class_type": "EmptySD3LatentImage", "inputs": {"width": job.get("width", 720), "height": job.get("height", 1280), "batch_size": 1}},
            "14": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler",
                                                        "scheduler": "simple", "positive": ["11", 0], "negative": ["12", 0], "latent_image": ["13", 0], "denoise": 1.0}},
            "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["6", 0]}},
            "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": f"{job['name']}_s{seed}"}},
        }
        run_graph(f"{job['name']}_s{seed}", g)
        src = sorted((COMFY / "output").glob(f"{job['name']}_s{seed}_*.png"))[-1]
        dst = OUT / f"{job['name']}_s{seed}.png"
        shutil.copy(src, dst)
        emit(dst)


def i2v(job, base):
    img = stage(base / job["image"])
    seed = job.get("seed", 7)
    sampler = dict(steps=4, cfg=1.0, sampler_name="euler", scheduler="simple", noise_seed=seed,
                   positive=["12", 0], negative=["12", 1])
    g = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": M("wan_i2v_high")}},
        "2": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": M("wan_i2v_low")}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": M("wan_i2v_lora_high"), "strength_model": 1.0}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["2", 0], "lora_name": M("wan_i2v_lora_low"), "strength_model": 1.0}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["3", 0], "shift": 5.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["4", 0], "shift": 5.0}},
        "7": {"class_type": "CLIPLoader", "inputs": {"clip_name": M("umt5"), "type": "wan"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": job["prompt"]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": job.get("negative", NEGATIVE)}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": M("wan_vae")}},
        "11": {"class_type": "LoadImage", "inputs": {"image": img}},
        "12": {"class_type": "WanImageToVideo", "inputs": {
            "positive": ["8", 0], "negative": ["9", 0], "vae": ["10", 0], "start_image": ["11", 0],
            "width": job.get("width", 480), "height": job.get("height", 832), "length": job.get("frames", 81), "batch_size": 1}},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {
            **sampler, "model": ["5", 0], "latent_image": ["12", 2], "add_noise": "enable",
            "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable"}},
        "14": {"class_type": "KSamplerAdvanced", "inputs": {
            **sampler, "model": ["6", 0], "latent_image": ["13", 0], "add_noise": "disable",
            "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable"}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["10", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": job["name"]}},
    }
    run_graph(job["name"], g)
    finish_video(job)


def s2v(job, base):
    """Same graph as ComfyUI's Wan 2.2 S2V template with the 4-step LoRA, unrolled for N chunks."""
    img, aud = stage(base / job["image"]), stage(base / job["audio"])
    seed, length = job.get("seed", 7), 77
    ks = dict(seed=seed, steps=4, cfg=1.0, sampler_name="uni_pc", scheduler="simple", denoise=1.0)
    g = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": M("wan_s2v")}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": M("wan_s2v_lora"), "strength_model": 1.0}},
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": M("umt5"), "type": "wan"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": job["prompt"]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": job.get("negative", NEGATIVE)}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": M("wan_vae")}},
        "8": {"class_type": "AudioEncoderLoader", "inputs": {"audio_encoder_name": M("wav2vec2")}},
        "9": {"class_type": "LoadAudio", "inputs": {"audio": aud}},
        "10": {"class_type": "AudioEncoderEncode", "inputs": {"audio_encoder": ["8", 0], "audio": ["9", 0]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": img}},
        "20": {"class_type": "WanSoundImageToVideo", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "vae": ["7", 0], "width": job.get("width", 480),
            "height": job.get("height", 832), "length": length, "batch_size": 1,
            "audio_encoder_output": ["10", 0], "ref_image": ["11", 0]}},
        "21": {"class_type": "KSampler", "inputs": {**ks, "model": ["3", 0], "positive": ["20", 0], "negative": ["20", 1], "latent_image": ["20", 2]}},
    }
    video = ["21", 0]
    for c in range(1, job.get("chunks", 2)):
        e, k, cat = str(30 + 3 * c), str(31 + 3 * c), str(32 + 3 * c)
        g[e] = {"class_type": "WanSoundImageToVideoExtend", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "vae": ["7", 0], "length": length, "video_latent": video,
            "audio_encoder_output": ["10", 0], "ref_image": ["11", 0]}}
        g[k] = {"class_type": "KSampler", "inputs": {**ks, "model": ["3", 0], "positive": [e, 0], "negative": [e, 1], "latent_image": [e, 2]}}
        g[cat] = {"class_type": "LatentConcat", "inputs": {"samples1": video, "samples2": [k, 0], "dim": "t"}}
        video = [cat, 0]
    g.update({
        "90": {"class_type": "LatentCut", "inputs": {"samples": video, "dim": "t", "index": 0, "amount": 1}},
        "91": {"class_type": "LatentConcat", "inputs": {"samples1": ["90", 0], "samples2": video, "dim": "t"}},
        "92": {"class_type": "VAEDecode", "inputs": {"samples": ["91", 0], "vae": ["7", 0]}},
        "93": {"class_type": "ImageFromBatch", "inputs": {"image": ["92", 0], "batch_index": 3, "length": 4096}},
        "94": {"class_type": "SaveImage", "inputs": {"images": ["93", 0], "filename_prefix": job["name"]}},
    })
    run_graph(job["name"], g)
    finish_video(job)


JOBS = {"qwen_edit": qwen_edit, "i2v": i2v, "s2v": s2v}


def main():
    jobs = []
    for f in glob.glob("/kaggle/input/**/jobs.json", recursive=True):
        jobs += [(j, Path(f).parent) for j in json.loads(Path(f).read_text())]
    log("jobs:", [(j["name"], j["type"]) for j, _ in jobs])
    install()
    download(sorted({k for j, _ in jobs for k in NEEDS[j["type"]]} | ({"esrgan"} if any(j.get("upscale") for j, _ in jobs) else set())))
    proc = start_server()
    try:
        for j, base in jobs:
            JOBS[j["type"]](j, base)
            step(f"job {j['name']}")
        for t in UPSCALERS:
            t.join()
        for t in REEMITS:
            t.join()
    finally:
        shutil.copy("/tmp/comfy.log", OUT / "comfy.log")
        (OUT / "timing.json").write_text(json.dumps(timing, indent=1))
        proc.terminate()
    log("ALL DONE", timing)
    # Last: every video again, upscaled copies last. Kaggle keeps only the tail (~7 MB) of a finished run's log,
    # so the newest outputs can always be recovered from run_log.json even if the live stream dropped them.
    vids = sorted(OUT.glob("*.mp4"), key=lambda f: (f.stem.endswith("_up"), f.stat().st_size))
    for f in vids:
        emit(f, again=False)
    log("FINAL EMIT DONE")


if __name__ == "__main__":
    main()
