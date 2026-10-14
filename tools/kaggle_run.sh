#!/usr/bin/env bash
# Run one of our GPU kernels on Kaggle (free ~30 GPU h/week) and download its output.
#
#   tools/kaggle_run.sh comfy_jobs IN_DIR OUT_DIR  # IN_DIR has jobs.json + images/audio (main one)
#   tools/kaggle_run.sh wan_i2v    IN_DIR OUT_DIR  # older: shots.json + start frames
#   tools/kaggle_run.sh musetalk   IN_DIR OUT_DIR  # older: talk.json + voice WAVs
#
# Needs KAGGLE_USERNAME + KAGGLE_API_TOKEN and the kaggle CLI (uv tool install kaggle).
# IN_DIR is uploaded as the private dataset <user>/maaran-<kernel>-in (a new version
# each run); the kernel is <user>/maaran-<kernel>. musetalk also mounts the latest
# wan_i2v output, so it can lip-sync a Wan clip. Runs on 2x T4; MACHINE=... to change
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
KSRC="[]"; [ "$KERNEL" = musetalk ] && KSRC="[\"$U/maaran-wan-i2v\"]"
cat > "$WORK/kernel/kernel-metadata.json" <<EOF
{"id": "$U/$SLUG", "title": "$SLUG", "code_file": "$KERNEL.py", "language": "python",
 "kernel_type": "script", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
 "machine_shape": "$MACHINE", "dataset_sources": ["$U/$SLUG-in"], "competition_sources": [],
 "kernel_sources": $KSRC, "model_sources": []}
EOF
kaggle kernels push -p "$WORK/kernel"

# 3. Wait, then download outputs and the log
sleep 30
while kaggle kernels status "$U/$SLUG" | grep -qE "RUNNING|QUEUED"; do sleep 60; done
kaggle kernels status "$U/$SLUG"
mkdir -p "$OUT"
kaggle kernels output "$U/$SLUG" -p "$OUT" -o -q 2>/dev/null || true
# Output files are also printed into the run log (comfy_jobs.py emit()); decode them, so
# results arrive even when Kaggle's output-file host is not reachable from here.
kaggle kernels logs "$U/$SLUG" > "$OUT/run_log.json" 2>/dev/null || true
python3 - "$OUT" <<'PY'
import base64, hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
try:
    lines = "".join(e["data"] for e in json.loads((out / "run_log.json").read_text())
                    if e.get("stream_name") == "stdout").splitlines()
except Exception as e:
    sys.exit(f"could not read run log: {e}")
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
        if ok:
            (out / cur[0]).write_bytes(data)
        print("decoded" if ok else "CORRUPT", cur[0], len(data))
        cur = None
    elif l.startswith("[") and ("== done" in l or "ALL DONE" in l or "failed" in l):
        print(l)
PY
ls -la "$OUT"
rm -rf "$WORK"
