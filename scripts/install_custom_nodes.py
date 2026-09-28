#!/usr/bin/env python3
"""Install the custom nodes listed in config/custom-nodes.json into a ComfyUI checkout.

Each node pack is cloned into ComfyUI/custom_nodes/<name> and checked out at the pinned ref.
Its requirements.txt is installed with the Python interpreter you run this script with.
Run it with ComfyUI's own Python (venv or python_embeded).

Examples:
  python scripts/install_custom_nodes.py --comfyui /path/to/ComfyUI
  python scripts/install_custom_nodes.py --comfyui ./ComfyUI --workflow pro-upscale
  python scripts/install_custom_nodes.py --comfyui ./ComfyUI --dry-run

Not handled here (see README "Installation"): the nunchaku wheel matching your torch/CUDA
version, and a CUDA build of llama-cpp-python for ComfyUI-QwenVL (GGUF).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], dry: bool, cwd: Path | None = None) -> None:
    print("  $", " ".join(cmd))
    if not dry:
        subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comfyui", required=True, type=Path, help="path to the ComfyUI folder (the one containing main.py)")
    ap.add_argument("--workflow", action="append", help="only install nodes used by this workflow folder name (repeatable)")
    ap.add_argument("--no-requirements", action="store_true", help="clone only, skip pip install")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "config" / "custom-nodes.json").read_text(encoding="utf-8"))
    target = args.comfyui / "custom_nodes"
    if not (args.comfyui / "main.py").exists():
        print(f"{args.comfyui} does not look like a ComfyUI folder (main.py missing)")
        return 2
    target.mkdir(exist_ok=True)

    for pack in cfg["custom_nodes"]:
        if args.workflow and not set(args.workflow) & set(pack["used_by"]):
            continue
        dest = target / pack["name"]
        print(f"\n[{pack['name']}] {pack['repo']} @ {pack['ref']}")
        existing = [d for d in target.iterdir() if d.is_dir() and d.name.lower() == pack["name"].lower()] if target.exists() else []
        if existing:
            dest = existing[0]
        if not dest.exists():
            run(["git", "clone", pack["repo"], str(dest)], args.dry_run)
        elif not (dest / ".git").exists():
            print(f"  {dest.name} exists but is not a git checkout (installed via Manager/registry?): left untouched."
                  f" Check that its version matches: {pack.get('validated_version', pack['ref'])}")
            continue
        else:
            print("  already present, fetching")
            run(["git", "fetch", "--tags", "origin"], args.dry_run, cwd=dest)
        run(["git", "checkout", pack["ref"]], args.dry_run, cwd=dest)
        req = dest / "requirements.txt"
        if not args.no_requirements and (args.dry_run or req.exists()):
            run([sys.executable, "-m", "pip", "install", "-r", str(req)], args.dry_run)
        if pack.get("extra"):
            print(f"  NOTE: {pack['extra']}")
    print("\nDone. Restart ComfyUI and check the console for import errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
