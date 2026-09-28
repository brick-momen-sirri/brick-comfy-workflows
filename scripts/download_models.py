#!/usr/bin/env python3
"""Download the models listed in config/models.json into ComfyUI/models.

  python scripts/download_models.py --comfyui /path/to/ComfyUI                 # everything
  python scripts/download_models.py --comfyui ./ComfyUI --workflow pro-upscale  # one workflow
  python scripts/download_models.py --comfyui ./ComfyUI --dry-run               # show the plan only

Gated Hugging Face files (FLUX.1-schnell VAE, FLUX.2 klein 9B, LTX 2.5) need you to accept the model
terms on huggingface.co and export HF_TOKEN=<your read token>. Internal models have no public
URL and are listed at the end so you can copy them manually.

Existing files are skipped. Downloads go to <file>.part first and are renamed when complete.
The script uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def human(mib: float | None) -> str:
    if mib is None:
        return "?"
    return f"{mib / 1024:.1f} GiB" if mib >= 1024 else f"{mib:.0f} MiB"


def download(url: str, dest: Path, token: str | None) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "brick-comfy-workflows/0.1"})
    if token and "huggingface.co" in url:
        req.add_header("Authorization", f"Bearer {token}")
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(8 << 20):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r    {done / total:6.1%} of {human(total / 2**20)}", end="", flush=True)
    print()
    tmp.replace(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comfyui", required=True, type=Path, help="path to the ComfyUI folder (models/ is created inside it)")
    ap.add_argument("--workflow", action="append", help="only models used by this workflow folder name (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    models = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))["models"]
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    base = args.comfyui / "models"
    selected = [m for m in models if not args.workflow or set(args.workflow) & set(m["used_by"])]
    internal = [m for m in selected if not m.get("download_url")]
    total = sum(m.get("size_mib") or 0 for m in selected if m.get("download_url"))
    print(f"{len(selected)} model files, about {human(total)} to download into {base}\n")

    failures = 0
    for m in selected:
        dest = base / m["folder"] / m["file"]
        if not m.get("download_url"):
            continue
        if dest.exists():
            print(f"[skip] {m['folder']}/{m['file']} (exists)")
            continue
        gated = m.get("auth", "").startswith("gated")
        print(f"[get ] {m['folder']}/{m['file']}  ({human(m.get('size_mib'))}{', gated' if gated else ''})")
        print(f"       {m['download_url']}")
        if args.dry_run:
            continue
        if gated and not token:
            print("       skipped: gated file, set HF_TOKEN after accepting the terms on Hugging Face")
            failures += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            download(m["download_url"], dest, token)
        except Exception as err:  # keep going; report at the end
            print(f"       FAILED: {err}")
            failures += 1

    if internal:
        print("\nInternal models (no public download yet, copy them manually):")
        for m in internal:
            print(f"  - models/{m['folder']}/{m['file']}  ({m.get('notes', '')})")
    free = shutil.disk_usage(base if base.exists() else args.comfyui).free / 2**30
    print(f"\nFree disk space: {free:.0f} GiB. Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
