# Validation report

Date: 2026-09-28. Status: **R&D**. The original image workflows are structurally validated, and one of them was executed end to end. They have not yet been run end to end on production hardware. The newly added video workflow has a separate record below; the original environment and image-runtime results remain historical.

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

The only findings were files not present on the test machine: `input.png` (a placeholder), the Fluxmania FP4 model, the Ultralytics and SAM models, and the BVFinish LoRA. On a fully provisioned machine, run it with `--strict-models`.

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

## LTX 2.5 video workflow

The supplied graph was inspected node by node and published as `ltx25_video_upscale.json` (32 editor nodes, including three reroutes and one setup note) and `ltx25_video_upscale.api.json` (28 processing nodes). It is a standalone adaptation, outside the Momi Forge parity comparison.

**Environment:** ComfyUI 0.37.0, frontend 1.53.6, Python 3.12.10, torch 2.8.0+cu128, Windows / RTX 4090. This is newer than the original image-workflow test environment above.

| Check | Result |
|---|---|
| Live `/object_info`: classes, required inputs, link types and widget values | 0 structural errors; all 28 processing nodes reach the saved video path |
| Editor load and API export | 0 unknown node types, 0 broken links; four loader warnings correspond to missing models. Same 28 processing nodes, input values and resolved links. API omits the frontend-only `Update inputs: null` button value emitted by KJNodes; one default display title differs. |
| Missing-file reporting | Four selected models unavailable: LTX 2.5 distilled INT8 transformer, Gemma 4 INT8 encoder, LTX 2.5 x2 latent upscaler, CQ Enhancer V2 LoRA. `input.mp4` is also a placeholder. |
| Frame-padding edge cases | Checked every input count from 1 to 4096: append 1–8 repeats, obtain `8n+1`, trim back without dropping source frames |
| Default timing/audio route | Input, conditioning and export agree at 24 fps; source audio connects to the video output; no initial frame skip |
| Installer/downloader workflow filters | Dry runs select 5 custom-node packs and 7 model files, with correct folders and gated-access flags |
| Model source verification | Exact files and sizes confirmed through the publishers' Hugging Face file listings; weights were not downloaded for this inspection |
| All four repository workflows, current static checker | Passed: 23 paths (16 General + 4 Pro + 2 Klein + 1 video), no structural errors; missing files remain warnings unless `--strict-models` is used |
| Offline regression tests | 6 tests pass: padding/trimming, timing/audio wiring, saved-video output detection, dynamic math inputs, V3 model combos and video encoder options |
| Full LTX 2.5 GPU render | **Not executed**: required models are missing; visual quality, audio sync, memory use and runtime model/sampler compatibility remain unverified |

The running installation wraps several nodes with Workflow Encrypt, so `/object_info` alone is not sufficient to identify their original packs. Their upstream implementation sources were also inspected: the existing KJNodes pin contains the required frame helpers; VideoHelperSuite supplies video IO, and Lightricks' LTXVideo supplies the looping sampler. The published dependency list points to those actual packs. This was not a clean installation of all pinned packs, and no runtime claim is made for the full graph.

The static validator now understands ComfyUI V3 combo options and named autogrow math inputs, VideoHelperSuite's format-specific widgets, missing video filenames, and saved video outputs. It still only reads node schemas and follows graph links; it does not queue a render or prove that model weights will load.

The [video guide](ltx25-video-upscale.md#changes-from-the-pasted-workflow) records the input/default changes and corrected padding expression. It also documents the difference between the supplied DiffVAE and CQdesign's Conv VAE recommendation.

```bash
python -m unittest discover -s tests -v
python scripts/validate_workflows.py --url http://localhost:8150 workflows/ltx25-video-upscale/ltx25_video_upscale.api.json
# After installing all models and uploading your input:
python scripts/validate_workflows.py --url http://localhost:8150 --strict-models workflows/ltx25-video-upscale/ltx25_video_upscale.api.json
```

For an actual media test, first replace the placeholder filename, cap the input at 49 or 97 frames and check the saved dimensions, frame count and audio sync. Then test a clip crossing temporal-window boundaries and compare against the original. No sample client media is included in this repository.
