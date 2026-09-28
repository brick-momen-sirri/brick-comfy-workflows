#!/usr/bin/env python3
"""Validate the API-format workflows in this repository against a running ComfyUI.

The script checks, per workflow:
  * every node class is installed (missing class = missing custom node)
  * required inputs are present, links point at existing outputs, and link types match
  * widget values are inside their allowed range/options (missing model files are reported
    separately, since they depend on what is downloaded on that machine)
  * every combination of the "Toggle · …" switches: which stages run with lazy Switch
    evaluation, and that each combination still reaches the SaveImage output
  * no absolute local paths or credential-looking strings are stored in the workflow

It only reads /object_info; nothing is queued or executed.

Usage:
  python scripts/validate_workflows.py                     # ComfyUI on http://127.0.0.1:8188
  python scripts/validate_workflows.py --url http://host:port
  python scripts/validate_workflows.py --object-info object_info.json workflows/pro-upscale/pro_upscale.api.json
  add --strict-models to fail when a referenced model file is not installed
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE_EXT = re.compile(r"\.(safetensors|pth|pt|ckpt|bin|gguf|onnx|sft|png|jpe?g|webp)$", re.I)
SECRET = re.compile(r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{16,}|api[_-]?key\s*[:=])", re.I)
ABS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users|root|mnt|runpod-volume|workspace)/)")
PRIMITIVES = {"PrimitiveBoolean", "PrimitiveInt", "PrimitiveFloat", "PrimitiveString", "PrimitiveStringMultiline"}


def is_link(v) -> bool:
    return isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int)


def load_object_info(args) -> dict:
    if args.object_info:
        return json.loads(Path(args.object_info).read_text(encoding="utf-8"))
    with urllib.request.urlopen(f"{args.url.rstrip('/')}/object_info", timeout=60) as r:
        return json.load(r)


def input_spec(info: dict, name: str):
    for section in ("required", "optional"):
        spec = (info["input"].get(section) or {}).get(name)
        if spec is not None:
            return section, spec
    return None, None


class Checker:
    def __init__(self, api: dict, oi: dict):
        self.api, self.oi = api, oi
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def out_type(self, link, seen=()):
        nid, slot = link
        node = self.api.get(nid)
        if node is None or node["class_type"] not in self.oi:
            return "*"
        if node["class_type"] == "ComfySwitchNode":
            if nid in seen:
                return "*"
            for key in ("on_true", "on_false"):
                v = node["inputs"].get(key)
                if is_link(v):
                    return self.out_type(v, seen + (nid,))
            return "*"
        outs = self.oi[node["class_type"]]["output"]
        return outs[slot] if slot < len(outs) else None

    @staticmethod
    def compatible(src, want) -> bool:
        if src is None:
            return False
        if isinstance(want, list):  # combo fed by a link (e.g. from a primitive): accept
            return True
        if "*" in (src, want) or "COMFY_MATCHTYPE_V3" in (src, want):
            return True
        return bool(set(str(src).split(",")) & set(str(want).split(",")))

    def check(self) -> None:
        for nid, node in self.api.items():
            ct = node.get("class_type")
            title = (node.get("_meta") or {}).get("title", "")
            where = f"[{nid}] {ct} “{title}”"
            info = self.oi.get(ct)
            if info is None:
                self.errors.append(f"{where}: node class not installed (missing custom node)")
                continue
            for name in (info["input"].get("required") or {}):
                if name not in node["inputs"]:
                    self.errors.append(f"{where}: required input '{name}' missing")
            for name, val in node["inputs"].items():
                section, spec = input_spec(info, name)
                if spec is None:
                    self.warnings.append(f"{where}: input '{name}' not defined by the installed node version")
                    continue
                want, opts = spec[0], (spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {})
                if is_link(val):
                    if val[0] not in self.api:
                        self.errors.append(f"{where}.{name}: links to missing node {val[0]}")
                        continue
                    src = self.out_type(val)
                    if not self.compatible(src, want):
                        self.errors.append(f"{where}.{name}: type {src} cannot feed {want}")
                    continue
                self.check_value(where, name, val, want, opts)
                if isinstance(val, str):
                    if SECRET.search(val):
                        self.errors.append(f"{where}.{name}: looks like a credential")
                    if ABS_PATH.search(val):
                        self.errors.append(f"{where}.{name}: absolute path {val!r}")

    def check_value(self, where, name, val, want, opts) -> None:
        if isinstance(want, list):
            if val not in want:
                if isinstance(val, str) and FILE_EXT.search(val):
                    self.warnings.append(f"{where}.{name}: '{val}' is not installed on this ComfyUI")
                else:
                    self.errors.append(f"{where}.{name}: {val!r} is not an allowed option")
            return
        if want in ("INT", "FLOAT"):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                self.errors.append(f"{where}.{name}: expected a number, got {val!r}")
                return
            lo, hi = opts.get("min"), opts.get("max")
            if (lo is not None and val < lo) or (hi is not None and val > hi):
                self.errors.append(f"{where}.{name}: {val} outside [{lo}, {hi}]")
        elif want == "BOOLEAN" and not isinstance(val, bool):
            self.errors.append(f"{where}.{name}: expected a boolean, got {val!r}")
        elif want == "STRING" and not isinstance(val, str):
            self.errors.append(f"{where}.{name}: expected text, got {val!r}")

    # ---------------------------------------------------------------- toggles
    def toggles(self) -> list[str]:
        return sorted((nid for nid, n in self.api.items()
                       if n["class_type"] == "PrimitiveBoolean" and (n.get("_meta") or {}).get("title", "").lower().startswith("toggle")),
                      key=lambda x: [int(p) if p.isdigit() else p for p in x.split(":")])

    def const_bool(self, v, values):
        if isinstance(v, bool):
            return v
        if is_link(v):
            node = self.api[v[0]]
            if node["class_type"] == "PrimitiveBoolean":
                return values.get(v[0], node["inputs"]["value"])
        return None

    def executed(self, values: dict) -> tuple[set, list[str]]:
        outputs = [nid for nid, n in self.api.items() if self.oi.get(n["class_type"], {}).get("output_node")]
        seen, notes = set(), []

        def visit(nid):
            if nid in seen or nid not in self.api:
                return
            seen.add(nid)
            node = self.api[nid]
            if node["class_type"] == "ComfySwitchNode":
                sw = self.const_bool(node["inputs"].get("switch"), values)
                if is_link(node["inputs"].get("switch")):
                    visit(node["inputs"]["switch"][0])
                branches = ["on_true", "on_false"] if sw is None else ["on_true" if sw else "on_false"]
                if sw is None:
                    notes.append(f"switch {nid} is driven by a non-constant value; both branches assumed")
                for b in branches:
                    if is_link(node["inputs"].get(b)):
                        visit(node["inputs"][b][0])
                return
            for v in node["inputs"].values():
                if is_link(v):
                    visit(v[0])

        for o in outputs:
            visit(o)
        return seen, notes


def stage_names(ui_path: Path) -> dict[str, str]:
    """Map top-level subgraph node id -> subgraph name, from the UI workflow next to the API file."""
    if not ui_path.exists():
        return {}
    ui = json.loads(ui_path.read_text(encoding="utf-8"))
    defs = {s["id"]: s.get("name", s["id"]) for s in (ui.get("definitions") or {}).get("subgraphs", [])}
    return {str(n["id"]): defs[n["type"]] for n in ui.get("nodes", []) if n.get("type") in defs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    ap.add_argument("--object-info", help="use a saved /object_info JSON instead of a live server")
    ap.add_argument("--strict-models", action="store_true", help="treat model files that are not installed as errors")
    args = ap.parse_args()
    files = args.files or sorted(ROOT.glob("workflows/*/*.api.json"))
    oi = load_object_info(args)
    failed = False
    for path in files:
        api = json.loads(path.read_text(encoding="utf-8"))
        c = Checker(api, oi)
        c.check()
        missing_models = [w for w in c.warnings if "is not installed" in w]
        other_warn = [w for w in c.warnings if w not in missing_models]
        if args.strict_models:
            c.errors += missing_models
        print(f"\n=== {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}  ({len(api)} nodes)")
        for e in c.errors:
            print(f"  ERROR    {e}")
        for w in other_warn:
            print(f"  WARNING  {w}")
        if missing_models:
            print(f"  MODELS   {len(missing_models)} referenced file(s) not installed here:")
            for w in sorted(set(m.split(': ', 1)[1] for m in missing_models)):
                print(f"           - {w}")
        stages = stage_names(path.with_name(path.name.replace(".api.json", ".json")))
        toggles = c.toggles()
        titles = {t: api[t]["_meta"]["title"] for t in toggles}
        print(f"  TOGGLES  {len(toggles)} → {2 ** len(toggles)} combinations")
        for combo in itertools.product((True, False), repeat=len(toggles)):
            values = dict(zip(toggles, combo))
            ran, notes = c.executed(values)
            save_ok = any(api[n]["class_type"] == "SaveImage" for n in ran)
            per_stage = {}
            for n in api:
                sg = n.split(":")[0] if ":" in n else None
                if sg in stages:
                    total, hit = per_stage.get(stages[sg], (0, 0))
                    per_stage[stages[sg]] = (total + 1, hit + (n in ran))
            ran_stages = [f"{name} ({hit}/{total})" for name, (total, hit) in sorted(per_stage.items()) if hit]
            label = ", ".join(f"{titles[t].split('·', 1)[-1].strip()}={'on' if v else 'off'}" for t, v in values.items())
            status = "ok " if save_ok else "NO OUTPUT"
            failed |= not save_ok
            print(f"    [{status}] {label}\n             runs {len(ran)} nodes; stage nodes run: {', '.join(ran_stages) or '(none: input passes through)'}")
            for n in notes:
                print(f"             note: {n}")
        failed |= bool(c.errors)
    print("\nRESULT:", "FAILED" if failed else "PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
