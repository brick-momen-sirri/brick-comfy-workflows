# Workflow details

**Copyright © 2026 Brick Visual — original contributions.** The [repository-wide notice](../NOTICE.md) applies to all four workflows and their documentation.

Stage-by-stage description of the three image graphs, and how each corresponds to the internal Momi Forge (Gradio) app. The app sends ComfyUI API workflows to RunPod serverless workers. It changes a few values and links per request, depending on the options the user picks. These editor workflows express the same routing with lazy **Switch** nodes, so the same graph works for every option.

## General Enhancement

The flow runs left to right on the canvas:

1. **Input.** `Input Image` provides the image. Its `MASK` output is the painted mask (Mask Editor), if any.
2. **Mask.** `Switch · Mask` picks the painted mask when `Use Painted Mask` is on. Otherwise it uses a full-image mask of 1.0 at the image size.
3. **Crop & Tile (900 px)** (subgraph):
   - `Inpaint Crop` crops the mask area with a 1.2× context. It pre-resizes the crop to at least 1280 and at most 5120 px, with 32 px mask blend and a 0.1 hi-pass filter.
   - The crop is split into `round(W/900) × round(H/900)` tiles with 5% overlap. The mask is tiled the same way.
   - Tiles are converted to lists (one entry per tile) and floored to a multiple of 16.
4. **Stage 1 · General Enhancement (SD1.5 epiCRealism)** (subgraph):
   - Model: epiCRealism Natural Sin RC1 + Detail Slider ALT2 LoRA (model strength = `details`, clip 1.0). The model is patched with Differential Diffusion and FreeU V2 (1.3 / 1.4 / 0.9 / 0.2).
   - Prompt, per tile: `Base Prompt` + a Qwen3-VL caption of the tile (resized to 512 px, preset "Simple Description"). A non-empty Custom Prompt replaces the preset instruction, as in the app. The negative prompt uses the `easynegative` and `epiCNegative` embeddings.
   - Sampler: KSampler, 30 steps, cfg 7, euler / normal, denoise = `denoise`, masked with `Set Latent Noise Mask`.
   - The internal *Caption Gate* skips Qwen3-VL when the stage is off. Its prompt node is an output node, so it would otherwise always run.
5. `Switch · General Enhancement` passes Stage 1's tiles, or the unprocessed tiles.
6. **Stage 2 · Advance Details (ReFocus + Flux)** (subgraph):
   - Each tile is blended with its 1x-ReFocus-V3 version (`sharpen`).
   - A Flux pass follows: Fluxmania Legacy (Nunchaku SVDQ fp4), guidance 3, dpmpp_2m / beta, 25 steps, denoise = `denoise`, masked. The prompt is `Base Prompt`, with no caption.
7. `Switch · Advance Details` passes Stage 2's tiles, or the tiles from step 5.
8. **Untile & Stitch** (subgraph): re-batch, resize the tiles back to the grid size, untile, and stitch back into the full image with the crop's blend mask.
9. `Switch · Tiled Result (General / Advance)` passes the stitched image when Stage 1 or 2 is on. Otherwise it passes the original input.
10. **Stage 3 · Body & Face Enhancement (FaceDetailer)** (subgraph):
    - The image is resized to 1280–5120 px.
    - FaceDetailer runs for people (YOLOv8m person seg + SAM ViT-B; guide 1024, denoise = `body denoise`), then for faces (YOLOv8m face bbox + face seg; denoise = `face denoise`).
    - It uses Flux (Fluxmania) with an empty prompt: 25 steps, cfg 1, dpmpp_2m / beta.
11. `Switch · Body & Face` passes the Stage 3 result or the image from step 9, then `Save Result`.

The Flux models (Fluxmania, CLIP-L + T5, FLUX VAE) sit in one **Flux Models** subgraph. Stages 2 and 3 share it, so the model loads once.

## Pro Upscale

**SeedVR2 engine (default).**

1. **Prepare & Tile** (subgraph):
   - The input's long side is limited to 12,800 px and raised to at least 768 px.
   - It is pre-scaled × `Upscale Factor` (lanczos) and capped at 10,240 px.
   - The result is split into `round(W/900) × round(H/900)` tiles (5% overlap), and each tile is resized to fit 512 px.
2. **SeedVR2 Upscale** (subgraph): the 7B sharp fp8-mixed DiT with the fp16 VAE. The VAE encodes and decodes in 1024 px tiles with 128 px overlap. Settings: shortest edge 1024, batch 1 (tiles processed one by one), LAB colour correction, seed 777.
3. **Flux Enhancement (Fluxmania · Nunchaku)** (subgraph), when the toggle is on:
   - Each tile is resized to fit 1024 px and run through a Flux img2img pass: guidance 3.5, euler / beta, fixed "realistic photo…" prompt.
   - Steps = round(c × 0.2125 + 3.75); denoise = c / 100, where c is `Flux Creativity`.
   - Decoding is tiled.
4. `Switch · Flux Enhancement` passes the Flux tiles or the SeedVR2 tiles.
5. **Reassemble Tiles** (subgraph): resizes the tiles back to the grid tile size and untiles.

**Super Fast engine.** The **Super Fast · 4xNomos8kDAT** subgraph upscales 4× with the model, then resizes by `factor / 4` (0.5 for ×2, 1.0 for ×4).

`Switch · Engine` picks the engine, then `Save Result`.

## Flux 2 Klein + RAW Enhancement

1. **Prepare Image (≈1 MP · ×32)** (subgraph): the input is scaled to about 1,048,576 px. The original is then resized into that size, rounded down to a multiple of 32, and padded with black.
2. **Load Models · Flux.2 Klein 9B** (subgraph): FLUX.2 [klein] 9B fp8, the Qwen3 8B fp8-mixed text encoder and the FLUX.2 VAE.
3. **RAW Enhancement · bvfinish LoRA + Qwen3-VL Caption** (subgraph):
   - The bvfinish LoRA is applied at strength 1.0.
   - Qwen3-VL captions the padded image (`max_tokens` 512, fixed seed). It uses the app's RAW captioning instruction, stored in the node's `custom_prompt`, which makes the caption start with `bvfinish`.
4. `Switch · Model (RAW LoRA)` and `Switch · Prompt (RAW caption)`: when RAW is on, the LoRA model and the caption are used. Otherwise the base model and the Edit Prompt are used.
5. **Flux.2 Klein Edit Sampler (4 steps)** (subgraph):
   - The input is VAE-encoded as a reference latent on both prompts. The negative prompt is empty; at cfg 1 it has no effect.
   - Sampling: euler, Flux2 scheduler, 4 steps, cfg 1, on an empty latent of the canvas size.
6. **Restore Original Size** (subgraph): fill/crop back to the exact input size, then `Save Result`.

## LTX 2.5 Video Upscale

The fourth workflow is a standalone video experiment. See [its complete guide](ltx25-video-upscale.md) for the processing stages, models, node packs, source-graph corrections and runtime limitations. It is not included in the image workflows’ Momi Forge parity comparison.

## Differences from the Momi Forge app

For the three image workflows, these differences are intentional. Everything else matches: same nodes, links and values for every option combination (see [validation.md](validation.md)).

| Area | App | This repository | Effect on results |
|---|---|---|---|
| Input | Re-encodes the upload as JPEG quality 75 and sends it as base64 (`ETN_LoadImageBase64`, or an upload to `LoadImage`) | Standard `LoadImage` of the original file | Small pixel differences, because there is no JPEG step |
| Mask (General Enhancement) | Red brush strokes on a Gradio layer, converted to a mask image | Painted in the ComfyUI Mask Editor (Load Image alpha), plus `Toggle · Use Painted Mask` | Same role; the app detected the mask automatically |
| Full-image mask (General Enhancement) | SolidMask(1) + SolidMask(0) combined with *add* | One SolidMask(1) | Identical mask |
| Tile-size constant (General Enhancement) | `easy int` (Easy-Use) | Core `PrimitiveInt` | Identical |
| Captioning (General Enhancement) | Qwen3-VL also ran in some combinations where its caption was unused (Stage 1 off) | Skipped when Stage 1 is off | Less compute; same output |
| Unused nodes | The API files carried leftovers (unused resize/size nodes in Pro Upscale; image 2/3 branches and other modes in Klein; base64 helpers in General Enhancement) | Removed | None |
| Switching | The app rewires links per request | Lazy `Switch` nodes driven by `Toggle · …` booleans | Same executed graph |
| Defaults | Some slider defaults were set by the app at request time (e.g. LoRA strength 1.0, body/face denoise 0.2) | Stored in the workflow | Same values |
| Seeds | Randomised by the app per request | `randomize` in the editor; set them yourself through the API | Same behaviour |
| LoRA path (Klein) | `Klein\Klein_9B_bvfinish_v01.safetensors` in the file, replaced by the app with the root name | Root name, no Windows subfolder | Same file |
| Klein modes | Edit (1–3 images), Reference Transfer, Consistency, RAW, Realistic | RAW, and 1-image Edit when RAW is off | Other modes not included |
