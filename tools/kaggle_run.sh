#!/usr/bin/env bash
# Run one of our GPU kernels on Kaggle (free ~30 GPU h/week) and download its output.
#
#   tools/kaggle_run.sh comfy_jobs IN_DIR OUT_DIR  # IN_DIR has jobs.json + images/audio
#
# Needs KAGGLE_USERNAME + KAGGLE_API_TOKEN and the kaggle CLI (uv tool install kaggle).
# IN_DIR is uploaded as the private dataset <user>/maaran-<kernel>-in (a new version
# each run); the kernel is <user>/maaran-<kernel>. Runs on 2x T4; MACHINE=... to change
# (NvidiaL4 is listed by the API but was not granted on the free tier: it ran CPU-only).
set -euo pipefail

KERNEL="$1"; IN="$2"; OUT="$3"
U="${KAGGLE_USERNAME:?set KAGGLE_USERNAME}"
MACHINE="${MACHINE:-NvidiaTeslaT4}"
SLUG="${SLUG:-maaran-${KERNEL//_/-}}"   # SLUG=... runs a second copy in parallel
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"

# 1. Inputs -> private dataset
cp -r "$IN"/. "$WORK/data"
# Credentials for the kernel's result upload (private dataset, owner's own account): see upload_outputs()
python3 -c 'import json,os,sys; json.dump({"username": os.environ["KAGGLE_USERNAME"], "key": os.environ["KAGGLE_API_TOKEN"], "out": sys.argv[1]}, open(sys.argv[2], "w"))' "$U/$SLUG-out" "$WORK/data/.kaggle_cred.json"
cat > "$WORK/data/dataset-metadata.json" <<EOF
{"title": "$SLUG-in", "id": "$U/$SLUG-in", "licenses": [{"name": "CC0-1.0"}]}
EOF
if kaggle datasets status "$U/$SLUG-in" >/dev/null 2>&1; then
  kaggle datasets version -p "$WORK/data" -m "run $(date -u +%FT%TZ)" -q
else
  kaggle datasets create -p "$WORK/data" -q
fi
until [ "$(kaggle datasets status "$U/$SLUG-in")" = "ready" ]; do sleep 10; done

# 2. Push the kernel (this starts a run)
mkdir "$WORK/kernel"
cp "$HERE/kaggle/$KERNEL.py" "$WORK/kernel/"
KSRC="[]"
cat > "$WORK/kernel/kernel-metadata.json" <<EOF
{"id": "$U/$SLUG", "title": "$SLUG", "code_file": "$KERNEL.py", "language": "python",
 "kernel_type": "script", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
 "machine_shape": "$MACHINE", "dataset_sources": ["$U/$SLUG-in"], "competition_sources": [],
 "kernel_sources": $KSRC, "model_sources": []}
EOF
kaggle kernels push -p "$WORK/kernel"
mkdir -p "$OUT"

# 3. Follow the live log the whole run (Kaggle keeps only the tail of a finished run's
#    log, and output files come from a host that may be blocked here), then wait
sleep 20
# The stream sometimes stalls without closing (Ep 2): restart it every 10 min until the run ends.
( while true; do
    PYTHONUNBUFFERED=1 timeout 600 kaggle kernels logs -f "$U/$SLUG" >> "$OUT/live_log.txt" 2>/dev/null
    kaggle kernels status "$U/$SLUG" | grep -qE "RUNNING|QUEUED" || break
    sleep 5
  done ) &
FOLLOW=$!
while kaggle kernels status "$U/$SLUG" | grep -qE "RUNNING|QUEUED"; do sleep 60; done
sleep 20; kill $FOLLOW 2>/dev/null || true
kaggle kernels status "$U/$SLUG"
kaggle kernels output "$U/$SLUG" -p "$OUT" -o -q 2>/dev/null || true
# Main channel: the kernel uploads its outputs as the private dataset $SLUG-out; wait until the new version is
# ready (it must be newer than this run's start), then download it.
for i in $(seq 1 30); do
  if [ "$(kaggle datasets status "$U/$SLUG-out" 2>/dev/null)" = "ready" ]; then
    rm -rf "$OUT/ds" && mkdir -p "$OUT/ds" && { kaggle datasets download "$U/$SLUG-out" -p "$OUT/ds" --unzip -q 2>/dev/null || true; }
    # the whole-dataset download 404s for a while after a new version; single files work sooner (Ep 10)
    if [ -z "$(ls "$OUT/ds")" ]; then
      for f in $(kaggle datasets files "$U/$SLUG-out" 2>/dev/null | awk 'NR>2 {print $1}'); do
        kaggle datasets download "$U/$SLUG-out" -f "$f" -p "$OUT/ds" -q 2>/dev/null || true
      done
      (cd "$OUT/ds" && for z in *.zip; do [ -f "$z" ] && unzip -oq "$z" && rm -f "$z"; done) || true
    fi
    if python3 - "$IN/jobs.json" "$OUT/ds" <<'PY'
import json, sys
from pathlib import Path
want = []
for j in json.loads(Path(sys.argv[1]).read_text()):
    want += ([f"{j['name']}_s{s}.png" for s in j.get("seeds", [7])] if j["type"] == "qwen_edit" else [f"{j['name']}.mp4"])
sys.exit(0 if all((Path(sys.argv[2]) / w).exists() for w in want) else 1)   # a stale older version lacks them
PY
    then
      cp -n "$OUT/ds"/* "$OUT"/ 2>/dev/null; echo "downloaded results dataset: $(ls "$OUT/ds" | tr '\n' ' ')"; break
    fi
  fi
  sleep 20
done
# Output files are also printed into the run log (comfy_jobs.py emit()); decode them, so
# results arrive even when Kaggle's output-file host is not reachable from here.
kaggle kernels logs "$U/$SLUG" > "$OUT/run_log.json" 2>/dev/null || true
python3 - "$OUT" <<'PY'
import base64, hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
lines = []
live = out / "live_log.txt"
if live.exists():
    lines += live.read_text(errors="replace").splitlines()
try:
    lines += "".join(e["data"] for e in json.loads((out / "run_log.json").read_text())
                     if e.get("stream_name") == "stdout").splitlines()
except Exception as e:
    print(f"could not read run log: {e}")
cur = None
for l in lines:
    if l.startswith("@@FILE "):
        _, name, size, sha = l.split()
        cur, parts = (name, int(size), sha), []
    elif l.startswith("@@B ") and cur:
        parts.append(l[4:])
    elif l == "@@END" and cur:
        data = base64.b64decode("".join(parts))
        ok = len(data) == cur[1] and hashlib.sha256(data).hexdigest() == cur[2]
        if ok and not (out / cur[0]).exists():
            (out / cur[0]).write_bytes(data)
            print("decoded", cur[0], len(data))
        elif not ok:
            print("incomplete copy skipped:", cur[0])
        cur = None
    elif l.startswith("[") and ("== done" in l or "ALL DONE" in l or "failed" in l):
        print(l)
PY
ls -la "$OUT"
rm -rf "$WORK"
