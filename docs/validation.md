# Validation report

Date: 2026-09-28. Status: **R&D**. The workflows are structurally validated, and one of them was executed end to end. They have not yet been run end to end on production hardware.

## Test environment

| | |
|---|---|
| Machine | Windows 11, NVIDIA RTX 4090 (24 GB) |
| ComfyUI | 0.12.3, frontend 1.38.13, Python 3.12.10, torch 2.10.0+cu128 |
| Custom nodes | Pinned versions from [config/custom-nodes.json](../config/custom-nodes.json) where installed locally (essentials 9d9f4be, Impact-Pack 8.28.2, Impact-Subpack 1.3.5, Custom-Scripts 1.2.5, QwenVL 2.0.0, KJNodes 1.2.8, post-processing 1.0.1, Easy-Use 1.3.4, nunchaku 1.2.0, SeedVR2 2.5.24) |
| Not installed locally | ComfyUI-Inpaint-CropAndStitch. For load and static checks, a stub with the exact node interface of upstream v3.0.17 was registered; it never executed. |

## 1. Same behaviour as the Momi Forge app

The app builds the final ComfyUI prompt by changing values and links in its API workflow, depending on the UI options:

- `General_Enhancement_v04.py`: `_apply_general_workflow_updates`, `_apply_branch_routing`
- `server_upscaler_with_flux_enhancement.py`: lines 382–414
- `flux2_klein_image_edit_9b_distilled.py`: `_apply_flux2_klein_workflow_updates` and its routing helpers

A checker replays this routing on the app's original API workflow for every option combination. It collects the nodes that feed `SaveImage` and compares them with the exported `.api.json` of this repository, evaluated with lazy Switch semantics, on three points:

- the set of processing nodes that run;
- every link of every node, after resolving switches;
- every value, except per-run seeds, file names and the output prefix.

| Workflow | Combinations | Result |
|---|---|---|
| General Enhancement | 16 (General × Advance × Body × mask) | ✅ all identical |
| Pro Upscale | 8 (engine × Flux × factor 2/4) | ✅ all identical |
| Flux 2 Klein + RAW | 2 (RAW on / off = app "Raw Enhancement" / one-image "Edit") | ✅ all identical |

The check caught one real problem during development. Core `PrimitiveFloat` rounds to one decimal, which would have turned the 0.35 detail-pass denoise into 0.3. As a result, float parameters are exposed as widgets on the stage nodes and keep the precision of the node they drive.

## 2. Loading in the ComfyUI frontend

Each editor workflow was loaded with `app.loadGraphData`. The check covered every node type at the top level and inside the subgraph definitions.

| Workflow | Unknown node types | Nodes with errors | Broken links | Editor → API round-trip |
|---|---|---|---|---|
| General Enhancement | 0 | 0 | 0 | identical to `general_enhancement.api.json` |
| Pro Upscale | 0 | 0 | 0 | identical to `pro_upscale.api.json` |
| Flux 2 Klein + RAW | 0 | 0 | 0 | identical to `flux2_klein_raw_enhancement.api.json` |

## 3. Static validation (`scripts/validate_workflows.py`)

The script checks the installed node definitions (`/object_info`): classes, required inputs, link types and value ranges. Result: **0 errors** in all three workflows.

The only findings were files not present on the test machine: `input.png` (a placeholder), the Fluxmania FP4 model, the Ultralytics and SAM models, and the internal bvfinish LoRA. On a fully provisioned machine, run it with `--strict-models`.

Every toggle combination reaches `Save Result` (22 combinations). The script also reports how many nodes of each stage run, e.g. with only Body & Face on:

```text
[ok ] General Enhancement=off, Advance Details=off, Body & Face Enhancement=on, Use Painted Mask=off
      runs 32 nodes; stage nodes run: Flux Models (Nunchaku · Fluxmania) (3/3), Stage 1 · General Enhancement (SD1.5 epiCRealism) (3/20), Stage 3 · Body & Face Enhancement (FaceDetailer) (16/16)
```

The 3 Stage 1 nodes are the cheap prompt helpers (an always-run output node plus the caption gate). The SD 1.5 model, the sampler and Qwen3-VL do not run.

## 4. Runtime checks

| Test | Result |
|---|---|
| **Lazy bypass.** A synthetic graph where the disabled branch contained a node that raises an error, fed with an image *list* (as the tiles are) | ✅ Switch off: run succeeded and the 3 list items passed through untouched. Switch on: the branch executed and raised, as expected. |
| **Flux 2 Klein + RAW, RAW off** | ✅ Full run on the RTX 4090: 52.6 s including model loading. 1216×832 input → 1216×832 output. The LoRA and Qwen3-VL were correctly skipped. |

## Not executed

| Workflow / state | Reason |
|---|---|
| General Enhancement (any state) | The Fluxmania SVDQ **FP4** model needs a Blackwell GPU. It, the Ultralytics/SAM models and the Crop&Stitch pack are not on the test machine. |
| Pro Upscale (any state) | Same FP4 model; the SeedVR2 7B fp8-mixed file is not on the test machine. ComfyUI validates every branch, so Super Fast alone cannot run without them. |
| Flux 2 Klein + RAW, RAW on | The Qwen3-VL GGUF files are not on the test machine (about 4.9 GB download). |

**Recommended next step:** run each workflow once with default toggles, and once with every stage enabled, on a Blackwell machine with all models. Our RunPod images qualify. Compare the results with the app's output for the same input.

## Reproducing

```bash
# static + toggle checks against your ComfyUI
python scripts/validate_workflows.py --url http://127.0.0.1:8188 [--strict-models]
```

The parity checker reads the internal app source and its original API workflows, so it is not part of this repository.
