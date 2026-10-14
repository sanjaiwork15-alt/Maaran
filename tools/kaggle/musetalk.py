"""Kaggle GPU kernel: lip-sync Thatha's mouth to his Tamil voice with MuseTalk 1.5 (MIT).

Pushed by tools/kaggle_run.sh. Reads every talk.json found under /kaggle/input:
    [{"name": "talk01", "video": "talk01.mp4", "audio": "L02.wav"}, ...]
Each file name is searched for anywhere under /kaggle/input, so the video can come
from the Wan kernel's output (kernel_sources) and the audio from a dataset.
Writes /kaggle/working/<name>_lipsync.mp4 (25 fps, with the voice) and timing.json.

MuseTalk is pinned close to its documented environment (Python 3.10, torch 2.0.1,
mmcv 2.0.1 / mmpose 1.1.0) in its own venv, so Kaggle's newer torch is left alone.
"""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

T0 = time.time()
MT = Path("/tmp/MuseTalk")
VENV = Path("/tmp/mtenv")
PY = VENV / "bin/python"
OUT = Path("/kaggle/working")
timing = {}


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sh(cmd, **kw):
    log("$", cmd)
    subprocess.run(cmd, shell=True, check=True, **kw)


def step(name):
    timing[name] = round(time.time() - T0, 1)
    log("== done:", name)


def find(name):
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not hits:
        raise SystemExit(f"not found under /kaggle/input: {name}")
    return hits[0]


def install():
    if subprocess.run("nvidia-smi", shell=True).returncode:
        raise SystemExit("No GPU attached: this machine_shape is not available to the account")
    sh("free -g")
    sh(f"git clone -q --depth 1 https://github.com/TMElyralab/MuseTalk {MT}")
    sh(f"{sys.executable} -m pip install -q uv")
    uv = f"VIRTUAL_ENV={VENV} UV_LINK_MODE=copy {sys.executable} -m uv"
    sh(f"{sys.executable} -m uv venv -q -p 3.10 {VENV}")
    # torch 2.0.1 from PyPI (CUDA 11.7). mmcv-lite has no compiled ops, which MuseTalk's
    # pose model (RTMPose) does not need; mmpose goes in without deps to skip chumpy,
    # an SMPL helper that will not build and is not used here. mmdet is not used either.
    sh(f"{uv} pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 "
       f"diffusers==0.30.2 accelerate==0.28.0 numpy==1.23.5 opencv-python==4.9.0.80 "
       f"soundfile==0.12.1 transformers==4.39.2 huggingface_hub==0.30.2 librosa==0.11.0 einops==0.8.1 "
       f"omegaconf ffmpeg-python moviepy 'imageio[ffmpeg]' requests tqdm 'setuptools<70' "
       f"mmengine==0.10.7 mmcv-lite==2.0.1 json_tricks munkres 'xtcocotools>=1.12' matplotlib scipy")
    sh(f"{uv} pip install --no-deps mmpose==1.1.0 mmdet==3.1.0")
    sh(f"{uv} pip install pycocotools shapely terminaltables six")
    # RTMPose's CSPNeXt backbone lives in mmdet, which imports mmcv.ops at load time.
    # A stub mmcv._ext satisfies those imports; any compiled op would raise if called.
    ext = subprocess.check_output([str(PY), "-c", "import mmcv, os; print(os.path.dirname(mmcv.__file__))"],
                                  text=True).strip()
    Path(ext, "_ext.py").write_text(
        "def __getattr__(name):\n"
        "    def missing(*a, **k):\n"
        "        raise NotImplementedError(f'mmcv compiled op {name} is not available (mmcv-lite)')\n"
        "    return missing\n")
    step("install")


def download():
    m = MT / "models"
    hf = f"{PY} -c \"from huggingface_hub import hf_hub_download as d; import sys; d(sys.argv[1], sys.argv[2], local_dir=sys.argv[3])\""
    for repo, f, d in [
        ("TMElyralab/MuseTalk", "musetalkV15/musetalk.json", m),
        ("TMElyralab/MuseTalk", "musetalkV15/unet.pth", m),
        ("stabilityai/sd-vae-ft-mse", "config.json", m / "sd-vae"),
        ("stabilityai/sd-vae-ft-mse", "diffusion_pytorch_model.bin", m / "sd-vae"),
        ("openai/whisper-tiny", "config.json", m / "whisper"),
        ("openai/whisper-tiny", "pytorch_model.bin", m / "whisper"),
        ("openai/whisper-tiny", "preprocessor_config.json", m / "whisper"),
        ("yzd-v/DWPose", "dw-ll_ucoco_384.pth", m / "dwpose"),
        # HuggingFace mirrors of the Google Drive / pytorch.org / adrianbulat.com files
        ("ManyOtherFunctions/face-parse-bisent", "79999_iter.pth", m / "face-parse-bisent"),
        ("ManyOtherFunctions/face-parse-bisent", "resnet18-5c106cde.pth", m / "face-parse-bisent"),
        ("ByteDance/LatentSync-1.5", "auxiliary/s3fd-619a316812.pth", Path("/tmp/s3fd")),
    ]:
        sh(f"{hf} {repo} {f} {d}")
    sh(f"cp /tmp/s3fd/auxiliary/s3fd-619a316812.pth {MT}/musetalk/utils/face_detection/detection/sfd/s3fd.pth")
    step("download")


def main():
    talks = []
    for f in glob.glob("/kaggle/input/**/talk.json", recursive=True):
        talks += json.loads(Path(f).read_text())
    log("talks:", talks)
    sh("find /kaggle/input -maxdepth 4 | head -50")
    install()
    download()
    cfg, data = [], MT / "data/maaran"
    data.mkdir(parents=True, exist_ok=True)
    for t in talks:
        # Wan clips are 16 fps; MuseTalk works at 25 fps.
        v = data / f"{t['name']}.mp4"
        sh(f"ffmpeg -loglevel error -y -i {find(t['video'])} -vf fps=25 -c:v libx264 -crf 12 -pix_fmt yuv420p {v}")
        a = data / f"{t['name']}.wav"
        sh(f"ffmpeg -loglevel error -y -i {find(t['audio'])} -ar 16000 -ac 1 {a}")
        cfg.append(f"{t['name']}:\n  video_path: \"{v}\"\n  audio_path: \"{a}\"\n  result_name: \"{t['name']}.mp4\"\n")
    (MT / "configs/inference/maaran.yaml").write_text("".join(cfg))
    t = time.time()
    sh(f"{PY} -m scripts.inference --inference_config configs/inference/maaran.yaml --result_dir /tmp/mtout "
       f"--unet_model_path models/musetalkV15/unet.pth --unet_config models/musetalkV15/musetalk.json "
       f"--version v15 --use_float16 --ffmpeg_path /usr/bin", cwd=MT)
    timing["musetalk_sec"] = round(time.time() - t, 1)
    for t in talks:  # MuseTalk logs and skips a failed task, so check every result exists
        res = Path(f"/tmp/mtout/v15/{t['name']}.mp4")
        if not res.exists():
            raise SystemExit(f"MuseTalk produced no video for {t['name']}")
        sh(f"cp {res} {OUT}/{t['name']}_lipsync.mp4")
    step("musetalk")
    (OUT / "timing.json").write_text(json.dumps(timing, indent=1))
    log("ALL DONE", timing)


main()
