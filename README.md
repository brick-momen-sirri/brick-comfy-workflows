# Brick Visual · ComfyUI Workflows

> ⚠️ These are **experimental R&D workflows** under active development and testing. Their nodes, models, settings and outputs may change as testing continues.

This repository contains three Brick Visual experiments for evaluating image-processing approaches in ComfyUI:

| Workflow | Research focus |
|---|---|
| [General Enhancement](#1-general-enhancement) | Testing tile-based refinement of architectural renders, with optional body and face enhancement |
| [Pro Upscale](#2-pro-upscale) | Comparing ×2 / ×4 SeedVR2 upscaling with an optional Flux detail pass against a faster single-model approach |
| [Flux 2 Klein + RAW Enhancement](#3-flux-2-klein--raw-enhancement) | Exploring photoreal enhancement of raw renders with Flux.2 Klein and the experimental BVFinish LoRA |

Each workflow is provided in two formats:

- **`<name>.json`**: the editor workflow, with subgraphs, groups, notes and toggles. Open it in ComfyUI.
- **`<name>.api.json`**: the same graph in API format, with the default toggle values. Use it for `/prompt` or serverless deployment.

The graphs preserve the current experimental pipelines in editable and API-ready forms. Every toggle combination has been checked for valid execution paths; [Validation](#validation) explains how this was tested. Implementation notes are listed in [docs/workflows.md](docs/workflows.md#differences-from-the-momi-forge-app).

---

## Contents

- [Repository structure](#repository-structure)
- [Included workflows](#included-workflows)
- [How the toggles work](#how-the-toggles-work)
- [Installation](#installation)
- [Custom nodes](#custom-nodes)
- [Required models](#required-models)
- [Model download instructions](#model-download-instructions)
- [Running the workflows](#running-the-workflows)
- [Validation](#validation)
- [Known limitations (R&D)](#known-limitations-rd)

---

## Repository structure

```text
brick-comfy-workflows/
├── README.md
├── workflows/
│   ├── general-enhancement/
│   │   ├── general_enhancement.json              # editor workflow (subgraphs, toggles)
│   │   └── general_enhancement.api.json          # API format, default toggles
│   ├── pro-upscale/
│   │   ├── pro_upscale.json
│   │   └── pro_upscale.api.json
│   └── flux2-klein-raw-enhancement/
│       ├── flux2_klein_raw_enhancement.json
│       └── flux2_klein_raw_enhancement.api.json
├── config/
│   ├── custom-nodes.json                         # node packs, repositories, pinned commits
│   └── models.json                               # model inventory, folders, verified download URLs
├── scripts/
│   ├── install_custom_nodes.py                   # clone + pin the node packs
│   ├── download_models.py                        # download models into ComfyUI/models
│   └── validate_workflows.py                     # static checks against a running ComfyUI
├── docs/
│   ├── workflows.md                              # stage-by-stage details, parity with the app
│   ├── api-usage.md                              # node IDs for inputs, toggles and parameters
│   └── validation.md                             # what was validated and how
└── examples/
    └── README.md                                 # input guidelines (no sample images, see note)
```

No model weights, generated images, credentials or local paths are stored in this repository.

---

## Included workflows

### 1. General Enhancement

`workflows/general-enhancement/general_enhancement.json`

**What it does.** It crops the working area (the whole image, or a painted mask) and resizes it to 1280–5120 px. It then splits the crop into ~900 px tiles, refines every tile, and blends the result back into the original image. The stages, all optional, are:

| Stage | Default | What happens |
|---|---|---|
| **Stage 1 · General Enhancement** | on | SD 1.5 (epiCRealism) img2img per tile at low denoise, with a detail LoRA. Each tile gets its own Qwen3-VL caption, appended to the prompt. |
| **Stage 2 · Advance Details** | off | Each tile is blended with a 1x-ReFocus version ("Sharpen"). A low-denoise Flux (Fluxmania, Nunchaku) pass follows. |
| **Stage 3 · Body & Face Enhancement** | off | FaceDetailer re-renders detected people, then faces, over the whole image. |

If Stages 1 and 2 are both off, no tiling happens. The original image then goes straight to Stage 3, or to the output.

**Inputs**

- `Input Image`: an RGB render. Painting a mask in the Load Image **Mask Editor** and enabling `Toggle · Use Painted Mask` limits Stages 1–2 to that area.
- `Custom Prompt` (optional): it is prepended to the style tags. Qwen3-VL also uses it as its instruction; this matches the app.

**Outputs:** one image (`Save Result`). The stages work in a 1280–5120 px range. When a stage runs, images outside that range are resized into it, so the output size can differ from the input; the app does the same.

**Toggles and controls**

| Control | Where | Default | Range used by the app |
|---|---|---|---|
| `Toggle · General Enhancement` | Controls | on | – |
| `Toggle · Advance Details` | Controls | off | – |
| `Toggle · Body & Face Enhancement` | Controls | off | – |
| `Toggle · Use Painted Mask` | Controls | off | – |
| `Custom Prompt` | Controls | empty | text |
| `details (0–2)` (LoRA strength) | Stage 1 node | 1.0 | 0–2 |
| `denoise (0–0.45)` | Stage 1 node | 0.10 | 0–0.45 |
| `sharpen (0–1)` | Stage 2 node | 0.40 | 0–1 |
| `denoise (0–0.7)` | Stage 2 node | 0.35 | 0–0.7 |
| `body denoise` / `face denoise` | Stage 3 node | 0.20 / 0.20 | 0–0.3 |

**Limitations**

- It needs 15 model files and 10 node packs, the largest dependency set of the three.
- The Fluxmania FP4 model needs a Blackwell GPU (see [limitations](#known-limitations-rd)).
- Very small crops (under ~450 px on a side after resizing) make the tile grid 0 rows or columns, and the tile node fails. The same happens in the app.
- The painted mask comes from the image's alpha channel (ComfyUI Mask Editor). The app used a red brush on a separate layer.

### 2. Pro Upscale

`workflows/pro-upscale/pro_upscale.json`

**What it does.**

- **SeedVR2 engine** (default): clamps the input size and pre-scales it by the upscale factor (capped at 10240 px). It splits the result into ~900 px tiles and restores each tile with SeedVR2 7B (sharp). An optional Flux img2img pass follows ("Creativity"), then the tiles are merged back.
- **Super Fast engine:** a single 4× model upscale (4xNomos8kDAT), then resized to the requested factor. Flux is not used.

**Inputs:** `Input Image` (RGB).

**Outputs:** one image, about ×2 or ×4 the input. With the SeedVR2 engine, a few edge pixels can be dropped by the tile grid; the app behaves the same way.

**Toggles and controls**

| Control | Default | Notes |
|---|---|---|
| `Toggle · SeedVR2 Engine (off = Super Fast)` | on | Off switches to the Super Fast engine |
| `Toggle · Flux Enhancement` | on | SeedVR2 engine only |
| `Upscale Factor (2 or 4)` | 2 | The app exposes ×2 and ×4 |
| `Flux Creativity (10–40)` | 30 | Steps = round(c × 0.2125 + 3.75) → 6–12; denoise = c / 100 → 0.10–0.40 |

**Limitations**

- SeedVR2 7B plus Flux on large outputs (8K) is GPU-heavy. This is our slowest workflow (p90 about 4 minutes).
- After pre-scaling, each side must be at least ~450 px, because the tile grid uses `round(side / 900)`. Inputs under 768 px on the long side are raised to 768 px first. Extreme aspect ratios (e.g. 3000×200 at ×2) still give a 0-row grid, and the tile node fails. The same happens in the app.

### 3. Flux 2 Klein + RAW Enhancement

`workflows/flux2-klein-raw-enhancement/flux2_klein_raw_enhancement.json`

**What it does.** It is a FLUX.2 [klein] 9B (distilled, 4 steps) reference-image edit. The input is scaled to about 1 MP and padded to a multiple of 32 px, and the result is cropped back to the input size.

- **RAW Enhancement on** (default): loads the **BVFinish** LoRA (strength 1.0). Qwen3-VL writes the prompt from the image, using a fixed captioning instruction that starts with the `bvfinish` trigger. The Edit Prompt is ignored.
- **RAW Enhancement off:** a plain Flux.2 Klein edit driven by the `Edit Prompt` (no LoRA, no captioning).

**Inputs:** `Input Image` (RGB); `Edit Prompt` (RAW off only).

**Outputs:** one image with the same size as the input.

**Toggles and controls**

| Control | Default |
|---|---|
| `Toggle · RAW Enhancement` | on |
| `Edit Prompt (used only when RAW is off)` | empty |

**Limitations**

- Only the one-image Edit and RAW modes of the app are included. Reference Transfer, Consistency and Realistic use other internal LoRAs and are out of scope here.
- FLUX.2 [klein] 9B is released under the FLUX Non-Commercial License.

---

## How the toggles work

Every optional stage is gated by the core ComfyUI **Switch** node (`ComfySwitchNode`), which evaluates its branches **lazily**:

```text
                  ┌──► [ Stage subgraph ] ──► on_true ───┐
 previous step ───┤                                      ├──► Switch ──► next step
                  └────────────────────────► on_false ───┘      ▲
                                                                 │ switch
                                              Toggle · … (Boolean node)
```

- The switch only requests the branch it needs. The nodes of a disabled stage are never executed: no model loading and no GPU time. This was verified at run time, see [docs/validation.md](docs/validation.md).
- The graph is identical in every state; only the boolean values change. Every combination of toggles is valid (16 for General Enhancement, 4 for Pro Upscale, 2 for Klein).
- For API/serverless use, toggles are plain inputs: set `inputs.value` on the `Toggle · …` nodes. The node IDs are in [docs/api-usage.md](docs/api-usage.md).
- The Switch widgets on the canvas are greyed out because they are driven by the toggle nodes. Change the **Toggle** nodes, not the switches.

Each stage is a named **subgraph**. Double-click it to open it; every subgraph has an *About this stage* note inside. The numeric parameters the app exposes appear directly on the stage nodes, so they keep the precision of the node they drive.

---

## Installation

### 1. ComfyUI

Use a recent ComfyUI that has the core **Switch** node (added December 2025) and a frontend with subgraph support.

- Validated with ComfyUI **0.12.3** / frontend **1.38.13**.
- Our RunPod images run ComfyUI **0.20–0.24** (frontend 1.42–1.44).

```bash
git clone https://github.com/Comfy-Org/ComfyUI
cd ComfyUI
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

Our RunPod images use Python 3.12, torch 2.10–2.11 (CUDA 12.8) and 32–96 GB GPUs; see [Known limitations](#known-limitations-rd).

### 2. Custom nodes

Run this with the same Python that runs ComfyUI:

```bash
python scripts/install_custom_nodes.py --comfyui /path/to/ComfyUI
# only what one workflow needs:
python scripts/install_custom_nodes.py --comfyui /path/to/ComfyUI --workflow pro-upscale
```

The script clones each pack from [config/custom-nodes.json](config/custom-nodes.json), checks out the pinned commit or tag, and installs its `requirements.txt`. You can also install the same repositories with ComfyUI-Manager.

### 3. Extra native dependencies

| Needed by | Package | Notes |
|---|---|---|
| ComfyUI-nunchaku | `nunchaku` wheel **1.2.1** | Pick the wheel that matches your torch, CUDA and Python from the [release page](https://github.com/nunchux-ai/nunchaku/releases/tag/v1.2.1), e.g. `nunchaku-1.2.1+cu12.8torch2.10-cp312-cp312-linux_x86_64.whl`. |
| ComfyUI-QwenVL (GGUF) | `llama-cpp-python` with CUDA + vision | Our images use the prebuilt wheels from [JamePeng/llama-cpp-python](https://github.com/JamePeng/llama-cpp-python/releases) (cu128). The CPU wheel from PyPI works but is slow. |
| ComfyUI-Impact-Subpack | `ultralytics` | Installed from its requirements; needed for the YOLO detectors. |

### 4. Models

See [Required models](#required-models) and [Model download instructions](#model-download-instructions).

---

## Custom nodes

The core ComfyUI nodes (samplers, loaders, `LoadImage`, `SaveImage`, `ComfySwitchNode`, `Primitive*`) are not listed.

| Node pack | Repository | Pinned ref | Why it is required | Used by |
|---|---|---|---|---|
| ComfyUI_essentials | [cubiq/ComfyUI_essentials](https://github.com/cubiq/ComfyUI_essentials) | `9d9f4be` | Conditional resizing, tile/untile grid, size maths, batch↔list conversion (`ImageResize+`, `ImageTile+`, `ImageUntile+`, `SimpleMath+`, …) | all three |
| ComfyUI-Inpaint-CropAndStitch | [lquesada/ComfyUI-Inpaint-CropAndStitch](https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch) | `8584b08` (3.0.17) | Crops the working area with context and blends the result back (`InpaintCropImproved`, `InpaintStitchImproved`) | General Enhancement |
| ComfyUI-Impact-Pack | [ltdrdata/ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) | `6a517eb` (8.28.2) | Body and face detailers, SAM loader, batch→list (`FaceDetailerPipe`, `ToDetailerPipe`, `SAMLoader`, …) | General Enhancement |
| ComfyUI-Impact-Subpack | [ltdrdata/ComfyUI-Impact-Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack) | `50c7b71` (1.3.5) | YOLO person and face detectors (`UltralyticsDetectorProvider`) | General Enhancement |
| ComfyUI-Custom-Scripts | [pythongosssss/ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) | `aac13aa` (1.2.5) | Prompt assembly with the app's append/tidy rules (`StringFunction`) | General Enhancement |
| ComfyUI-QwenVL | [1038lab/ComfyUI-QwenVL](https://github.com/1038lab/ComfyUI-QwenVL) | `517aed6` (2.3.1) | Qwen3-VL captioning: per-tile captions, and the RAW prompt (`AILab_QwenVL_GGUF`) | General Enhancement, Klein |
| ComfyUI-KJNodes | [kijai/ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | `20a283e` (1.2.8) | Pass-through and 512 px resize for captioning (`ImagePass`, `ImageResizeKJv2`) | General Enhancement |
| ComfyUI-post-processing-nodes | [EllangoK/ComfyUI-post-processing-nodes](https://github.com/EllangoK/ComfyUI-post-processing-nodes) | `c96ce3b` (1.0.1) | The Sharpen blend (`Blend`) | General Enhancement |
| ComfyUI-Easy-Use | [yolain/ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) | `v1.3.4` | Re-batching tiles before untiling, as in the app (`easy imageListToImageBatch`) | General Enhancement |
| ComfyUI-nunchaku | [nunchux-ai/ComfyUI-nunchaku](https://github.com/nunchux-ai/ComfyUI-nunchaku) | `v1.2.1` | Loads the SVDQuant 4-bit Fluxmania model (`NunchakuFluxDiTLoader`) | General Enhancement, Pro Upscale |
| ComfyUI-SeedVR2_VideoUpscaler | [numz/ComfyUI-SeedVR2_VideoUpscaler](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler) | `4490bd1` (2.5.24) | SeedVR2 DiT/VAE loaders and upscaler | Pro Upscale |

Per workflow:

- **General Enhancement:** essentials, Inpaint-CropAndStitch, Impact-Pack, Impact-Subpack, Custom-Scripts, QwenVL, KJNodes, post-processing, Easy-Use, nunchaku (10 packs).
- **Pro Upscale:** essentials, SeedVR2, nunchaku (3 packs).
- **Flux 2 Klein + RAW:** essentials, QwenVL (2 packs).

The editor `.json` files store widget values by position, so keep the pinned versions. The `.api.json` files use named inputs and are less sensitive to node versions.

---

## Required models

All download locations were checked on 2026-09-28. When the official publisher does not host the file on Hugging Face, the table links the Hugging Face mirror our RunPod images download from, and the official page. The machine-readable version, with sizes and licences, is [config/models.json](config/models.json).

| Model | Type | Used By | ComfyUI Location | Source |
|---|---|---|---|---|
| `svdq-fp4_r32-fluxmania-legacy.safetensors` | Diffusion model (FLUX.1-dev fine-tune, Nunchaku SVDQuant FP4) | General Enhancement, Pro Upscale | `models/diffusion_models/` | [spooknik/Fluxmania-SVDQ](https://huggingface.co/spooknik/Fluxmania-SVDQ) |
| `clip_l.safetensors` | Text encoder (CLIP-L) | General Enhancement, Pro Upscale | `models/text_encoders/` | [comfyanonymous/flux_text_encoders](https://huggingface.co/comfyanonymous/flux_text_encoders) |
| `t5xxl_fp8_e4m3fn_scaled.safetensors` | Text encoder (T5-XXL, fp8 scaled) | General Enhancement, Pro Upscale | `models/text_encoders/` | [comfyanonymous/flux_text_encoders](https://huggingface.co/comfyanonymous/flux_text_encoders) |
| `ae.safetensors` | VAE (FLUX.1) | General Enhancement, Pro Upscale | `models/vae/` | [black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) (gated) |
| `epicrealism_naturalSinRC1VAE.safetensors` | Checkpoint (SD 1.5, epiCRealism Natural Sin RC1 VAE) | General Enhancement | `models/checkpoints/` | Mirror: [philz1337x/epicrealism](https://huggingface.co/philz1337x/epicrealism) · Official: [Civitai](https://civitai.com/models/25694?modelVersionId=143906) |
| `detailSliderALT2.safetensors` | LoRA (SD 1.5, Detail Slider ALT2) | General Enhancement | `models/loras/` | Mirror: [iamanaiart/flatloras](https://huggingface.co/iamanaiart/flatloras) · Official: [Civitai](https://civitai.com/models/123543?modelVersionId=134717) |
| `easynegative.safetensors` | Textual inversion (SD 1.5 negative embedding) | General Enhancement | `models/embeddings/` | Mirror: [embed/EasyNegative](https://huggingface.co/embed/EasyNegative) · Official: [Civitai](https://civitai.com/models/7808?modelVersionId=9208) |
| `epiCNegative.pt` | Textual inversion (SD 1.5 negative embedding) | General Enhancement | `models/embeddings/` | Mirror: [dn118/epicnegative](https://huggingface.co/dn118/epicnegative) · Official: [Civitai](https://civitai.com/models/89484?modelVersionId=95263) |
| `1x-ReFocus-V3.pth` | Upscale model (ESRGAN 1x, sharpening) | General Enhancement | `models/upscale_models/` | Mirror: [notkenski/upscalers](https://huggingface.co/notkenski/upscalers) · Official: [OpenModelDB](https://openmodeldb.info/models/1x-ReFocus-V3) |
| `Qwen3VL-4B-Instruct-Q8_0.gguf` | Vision-language model (Qwen3-VL 4B Instruct, GGUF Q8_0) | General Enhancement, Flux 2 Klein + RAW | `models/llm/GGUF/Qwen/Qwen3-VL-4B-Instruct-GGUF/` | [Qwen/Qwen3-VL-4B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF) |
| `mmproj-Qwen3VL-4B-Instruct-F16.gguf` | Vision projector for Qwen3-VL 4B (GGUF F16) | General Enhancement, Flux 2 Klein + RAW | `models/llm/GGUF/Qwen/Qwen3-VL-4B-Instruct-GGUF/` | [Qwen/Qwen3-VL-4B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF) |
| `sam_vit_b_01ec64.pth` | Segmentation model (Segment Anything ViT-B) | General Enhancement | `models/sams/` | [Meta download](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth) (no official HF `.pth`) |
| `face_yolov8m.pt` | Detector (YOLOv8m face, bbox) | General Enhancement | `models/ultralytics/bbox/` | [Bingsu/adetailer](https://huggingface.co/Bingsu/adetailer) |
| `person_yolov8m-seg.pt` | Detector (YOLOv8m person, segmentation) | General Enhancement | `models/ultralytics/segm/` | [Bingsu/adetailer](https://huggingface.co/Bingsu/adetailer) |
| `face_yolov8m-seg_60.pt` | Detector (YOLOv8m face, segmentation) | General Enhancement | `models/ultralytics/segm/` | [GitHub release](https://github.com/hben35096/assets/releases/download/yolo8/face_yolov8m-seg_60.pt) (no HF repo found) |
| `seedvr2_ema_7b_sharp_fp8_e4m3fn_mixed_block35_fp16.safetensors` | SeedVR2 DiT (7B sharp, fp8 mixed) | Pro Upscale | `models/SEEDVR2/` | [AInVFX/SeedVR2_comfyUI](https://huggingface.co/AInVFX/SeedVR2_comfyUI) |
| `ema_vae_fp16.safetensors` | SeedVR2 VAE | Pro Upscale | `models/SEEDVR2/` | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) |
| `4xNomos8kDAT.pth` | Upscale model (DAT 4x, Super Fast engine) | Pro Upscale | `models/upscale_models/` | Mirror: [uwg/upscaler](https://huggingface.co/uwg/upscaler) · Official: [Phhofm/models](https://github.com/Phhofm/models/releases/tag/4xNomos8kDAT) |
| `flux-2-klein-9b-fp8.safetensors` | Diffusion model (FLUX.2 [klein] 9B distilled, fp8) | Flux 2 Klein + RAW | `models/diffusion_models/` | [black-forest-labs/FLUX.2-klein-9b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8) (gated) |
| `qwen_3_8b_fp8mixed.safetensors` | Text encoder (Qwen3 8B, fp8 mixed) | Flux 2 Klein + RAW | `models/text_encoders/` | [Comfy-Org/flux2-klein-9B](https://huggingface.co/Comfy-Org/flux2-klein-9B) (`split_files/text_encoders/`) |
| `flux2-vae.safetensors` | VAE (FLUX.2) | Flux 2 Klein + RAW | `models/vae/` | [Comfy-Org/flux2-dev](https://huggingface.co/Comfy-Org/flux2-dev) (`split_files/vae/`) |
| `Klein_9B_bvfinish_v01.safetensors` | LoRA (FLUX.2 [klein] 9B, RAW Enhancement) | Flux 2 Klein + RAW | `models/loras/` | [BrickMomen/raw-enhancement](https://huggingface.co/BrickMomen/raw-enhancement) |

Approximate download size per workflow: **General Enhancement 20.6 GB**, **Pro Upscale 22.1 GB**, **Flux 2 Klein + RAW 23.7 GB**. The Fluxmania model, Flux text encoders and VAE (about 12.8 GB) are shared by General Enhancement and Pro Upscale, and the Qwen3-VL files (5.1 GB) by General Enhancement and Klein.

---

## Model download instructions

**Scripted** (standard library only; files that already exist are skipped):

```bash
export HF_TOKEN=hf_xxx        # needed for the two gated Black Forest Labs files
python scripts/download_models.py --comfyui /path/to/ComfyUI --dry-run            # show the plan
python scripts/download_models.py --comfyui /path/to/ComfyUI                      # everything
python scripts/download_models.py --comfyui /path/to/ComfyUI --workflow pro-upscale
```

Before downloading the gated files, open [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) and [FLUX.2-klein-9b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8) once while logged in and accept the terms.

**Manual:** download the files from the table and place them like this. Only the folders these workflows use are shown:

```text
ComfyUI/
└── models/
    ├── checkpoints/
    │   └── epicrealism_naturalSinRC1VAE.safetensors
    ├── diffusion_models/
    │   ├── svdq-fp4_r32-fluxmania-legacy.safetensors
    │   └── flux-2-klein-9b-fp8.safetensors
    ├── text_encoders/
    │   ├── clip_l.safetensors
    │   ├── t5xxl_fp8_e4m3fn_scaled.safetensors
    │   └── qwen_3_8b_fp8mixed.safetensors
    ├── vae/
    │   ├── ae.safetensors
    │   └── flux2-vae.safetensors
    ├── loras/
    │   ├── detailSliderALT2.safetensors
    │   └── Klein_9B_bvfinish_v01.safetensors
    ├── embeddings/
    │   ├── easynegative.safetensors                 # save with this lower-case name
    │   └── epiCNegative.pt
    ├── upscale_models/
    │   ├── 1x-ReFocus-V3.pth
    │   └── 4xNomos8kDAT.pth
    ├── SEEDVR2/
    │   ├── seedvr2_ema_7b_sharp_fp8_e4m3fn_mixed_block35_fp16.safetensors
    │   └── ema_vae_fp16.safetensors
    ├── sams/
    │   └── sam_vit_b_01ec64.pth
    ├── ultralytics/
    │   ├── bbox/face_yolov8m.pt
    │   └── segm/
    │       ├── person_yolov8m-seg.pt
    │       └── face_yolov8m-seg_60.pt
    └── llm/GGUF/Qwen/Qwen3-VL-4B-Instruct-GGUF/
        ├── Qwen3VL-4B-Instruct-Q8_0.gguf
        └── mmproj-Qwen3VL-4B-Instruct-F16.gguf
```

Notes:

- ComfyUI-QwenVL and the SeedVR2 node can download their models on first use. Pre-downloading avoids a long first run.
- `text_encoders/` can also be the legacy `clip/` folder, since both are searched.
- On Linux, file and folder names are case-sensitive (`SEEDVR2`, `llm`, `easynegative.safetensors`).

---

## Running the workflows

**In the ComfyUI editor**

1. Drag a `workflows/<name>/<name>.json` file onto the canvas.
2. Load an image into `Input Image`.
3. Set the **Toggle** nodes and the stage parameters.
4. Run. Results are saved under `output/BrickVisual/`.

**Through the API:** use the `.api.json` files. Upload the image (`POST /upload/image`, or the `images` array of a worker-comfyui payload), set `inputs.image` on node `1`, and set the toggles or parameters by node ID. Then `POST /prompt`. [docs/api-usage.md](docs/api-usage.md) has the node ID tables and a Python example. For per-run randomness, as in the app, randomise the listed seed inputs before each request.

---

## Validation

Summary; details and reproduction steps are in [docs/validation.md](docs/validation.md).

| Check | Result |
|---|---|
| **Same behaviour as the Momi Forge app.** For every toggle combination, the app's own routing is replayed on its original API workflow and compared with these graphs, node by node and input by input (26 combinations) | ✅ identical processing nodes, links and values. Intentional differences are listed in [docs/workflows.md](docs/workflows.md#differences-from-the-momi-forge-app) |
| Loads in the ComfyUI frontend with no missing-node errors, no broken links; editor → API export round-trip is identical | ✅ all three (ComfyUI 0.12.3 / frontend 1.38.13). Inpaint-CropAndStitch was not installed on the test machine, so it was checked against its published v3.0.17 node interface |
| Static validation against the installed node definitions (types, required inputs, value ranges) | ✅ 0 errors |
| Every toggle combination reaches `Save Result`; disabled stages are not executed | ✅ 22 combinations checked by `validate_workflows.py`. Lazy skipping was also confirmed by a run in which the disabled branch would have raised an error |
| End-to-end GPU run | ✅ Flux 2 Klein with RAW off (RTX 4090, 52 s, output size = input size). The other runs need models not present on the test machine, see [validation.md](docs/validation.md#not-executed) |
| No local absolute paths, credentials or client images in the repository | ✅ |

Re-run the static checks on any ComfyUI with the nodes installed:

```bash
python scripts/validate_workflows.py --url http://127.0.0.1:8188
python scripts/validate_workflows.py --url http://127.0.0.1:8188 --strict-models   # also require all model files
```

---

## Known limitations (R&D)

- **R&D status.** Defaults, models and graph structure may still change. Do not treat outputs as final deliverables without review.
- **GPU.** The Fluxmania SVDQuant **FP4** model requires an NVIDIA **Blackwell** GPU (RTX 50xx / RTX PRO 6000). Our RunPod endpoints for these two workflows use 32 GB and 96 GB Blackwell-class GPUs. On Ada or Ampere GPUs, download `svdq-int4_r32-fluxmania-legacy.safetensors` from the same repository and select it in the Nunchaku loader (not validated).
- **All branches must be installed.** ComfyUI validates every node in the graph, including branches a toggle disables. For example, "Super Fast only" still needs the SeedVR2 and Flux models present.
- **Input preparation differs slightly from the app.** The app re-encodes inputs as JPEG (quality 75) before sending them; these workflows read the file as is. Expect small pixel-level differences.
- **Tile edge cases.** Very small crops or extreme aspect ratios can produce a 0-row/0-column tile grid, and the tile node fails (also true in the app).
- **Experimental core node.** `ComfySwitchNode` is still marked *beta* in ComfyUI and is shown with a BETA badge.
- **Node versions.** Editor workflows store widget values by position. Use the pinned node versions, or re-check values after updating node packs.
- **Mask input.** The General Enhancement mask comes from the Load Image alpha channel (Mask Editor). Through the API, send an RGBA PNG whose transparent area is the region to enhance, and enable `Toggle · Use Painted Mask`.
