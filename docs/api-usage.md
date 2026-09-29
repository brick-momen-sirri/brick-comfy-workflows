# API usage

**Copyright © 2026 Brick Visual — original contributions.** All API workflows are covered by the [repository-wide notice](../NOTICE.md); third-party rights and terms remain applicable.

Use the `*.api.json` files for `POST /prompt` or a serverless worker. They are the flattened form of the editor workflows, so nodes inside a subgraph have IDs like `219:138`: `<subgraph node id>:<inner node id>`. These IDs are stable as long as the editor workflow is not restructured.

In the three image workflows:

- **input image**: node `1` (`LoadImage`), `inputs.image` = the uploaded file name
- **output**: the `Save Result` node (`SaveImage`)

## General Enhancement: `workflows/general-enhancement/general_enhancement.api.json`

| Node | Input | Meaning | Default |
|---|---|---|---|
| `1` | `image` | Input image file name (RGBA allowed; the transparent area is the mask) | `input.png` |
| `2` | `value` | Toggle · General Enhancement (Stage 1) | `true` |
| `3` | `value` | Toggle · Advance Details (Stage 2) | `false` |
| `4` | `value` | Toggle · Body & Face Enhancement (Stage 3) | `false` |
| `5` | `value` | Toggle · Use Painted Mask (limits Stages 1–2 to the mask) | `false` |
| `6` | `value` | Custom Prompt | `""` |
| `219:122` | `strength_model` | Details (detail LoRA strength), app range 0–2 | `1.0` |
| `219:138` | `denoise` | General enhance denoise, app range 0–0.45 | `0.1` |
| `223:163` | `blend_factor` | Sharpen (ReFocus blend), app range 0–1 | `0.4` |
| `223:169` | `denoise` | Additional detail pass denoise, app range 0–0.7 | `0.35` |
| `227:214` | `denoise` | Body enhancement denoise, app range 0–0.3 | `0.2` |
| `227:215` | `denoise` | Face enhancement denoise, app range 0–0.3 | `0.2` |
| `26` | – | Output (`SaveImage`) | |

- **Randomised per run in the app:** `219:138.seed`, `223:170.noise_seed`, `227:214.seed`, `227:215.seed`.
- **Fixed:** the Qwen3-VL caption seed `219:125.seed`.

## Pro Upscale: `workflows/pro-upscale/pro_upscale.api.json`

| Node | Input | Meaning | Default |
|---|---|---|---|
| `1` | `image` | Input image file name | `input.png` |
| `2` | `value` | Toggle · SeedVR2 Engine (`false` = Super Fast, 4xNomos8kDAT) | `true` |
| `3` | `value` | Toggle · Flux Enhancement (SeedVR2 engine only) | `true` |
| `4` | `value` | Upscale factor, `2` or `4` | `2` |
| `5` | `value` | Flux creativity, 10–40 (steps 6–12, denoise 0.10–0.40) | `30` |
| `22` | – | Output (`SaveImage`) | |

- **Randomised per run in the app:** `179:143.noise_seed`.
- **Fixed:** the SeedVR2 seed `177:122.seed` (`777`).

## Flux 2 Klein + RAW Enhancement: `workflows/flux2-klein-raw-enhancement/flux2_klein_raw_enhancement.api.json`

| Node | Input | Meaning | Default |
|---|---|---|---|
| `1` | `image` | Input image file name | `input.png` |
| `2` | `value` | Toggle · RAW Enhancement | `true` |
| `3` | `value` | Edit prompt (used only when RAW Enhancement is off) | `""` |
| `22` | – | Output (`SaveImage`) | |

- **Randomised per run in the app:** `159:139.noise_seed`.
- **Fixed:** the Qwen3-VL caption seed `157:121.seed`.

## LTX 2.5 Video Upscale: `workflows/ltx25-video-upscale/ltx25_video_upscale.api.json`

This workflow uses plain node IDs and has no toggles. Place the video in ComfyUI's `input/` folder or upload it with the VHS upload control. Set node `29`'s `video` to that relative filename.

| Node | Input | Meaning | Default |
|---|---|---|---|
| `29` | `video` | Input video filename | `input.mp4` |
| `29` | `force_rate` | Resample input to this fps | `24` |
| `29` | `skip_first_frames` | Frames skipped at the start | `0` |
| `29` | `frame_load_cap` | Maximum loaded frames; 0 = all | `0` |
| `29` | `select_every_nth` | Frame stride; keep 1 for default audio timing | `1` |
| `5` | `strength_model` | CQ Enhancer V2 strength | `1.0` |
| `14` | `noise_seed` | Diffusion seed | `42` |
| `15` | `steps`, `denoise` | Refinement schedule | `4`, `0.15` |
| `33` | `video_cfg`, `audio_cfg` | Guidance scales | `1`, `1` |
| `71` | `temporal_tile_size`, `temporal_overlap` | Sampling windows, in frames | `144`, `48` |
| `10` | `frame_rate` | Conditioning fps; align with input/output | `24` |
| `74` | `custom_prompt`, `seed` | First-frame caption instruction/seed | empty, `179095357` |
| `7` | `text` | Caption link; replace with text for a manual prompt | `["74", 0]` |
| `40` | `frame_rate` | Export fps; align with input/conditioning | `24` |
| `40` | `filename_prefix` | Saved MP4 prefix | `BrickVisual/LTX25_Upscale` |
| `40` | `crf` | H.264 quality setting | `23` |
| `40` | `save_output` | Save under output/ | `true` |

```python
wf = json.load(open("workflows/ltx25-video-upscale/ltx25_video_upscale.api.json", encoding="utf-8"))
wf["29"]["inputs"]["video"] = "my_clip.mp4"
wf["29"]["inputs"]["frame_load_cap"] = 49  # short initial memory test
# Then submit wf as the prompt using the request example below.
```

The loader, conditioning and encoder rates must agree; changing the export rate alone alters speed/audio sync. `frame_load_cap` counts the loaded, resampled frames. The editor randomizes the Qwen caption seed after generation; API clients must update `74.seed` explicitly if they want that behavior. The diffusion seed remains fixed unless changed.

Results are emitted by `VHS_VideoCombine` at node `40` (video metadata, commonly under `gifs` in ComfyUI history), rather than `SaveImage`. A serverless handler must upload video files and collect video outputs explicitly; the image-only RunPod payload below does not implement this. See the [video guide](ltx25-video-upscale.md) before running.

## Example: ComfyUI `/prompt`

```python
import json, random, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
wf = json.load(open("workflows/pro-upscale/pro_upscale.api.json", encoding="utf-8"))

# 1. upload the input with POST /upload/image (multipart field "image"), then reference it:
wf["1"]["inputs"]["image"] = "my_render.png"
# 2. toggles / parameters
wf["2"]["inputs"]["value"] = True      # SeedVR2 engine
wf["3"]["inputs"]["value"] = False     # no Flux enhancement
wf["4"]["inputs"]["value"] = 4         # x4
# 3. fresh seed per run, like the app
wf["179:143"]["inputs"]["noise_seed"] = random.randint(0, 999_999_999_999)

req = urllib.request.Request(f"{COMFY}/prompt", method="POST",
                             data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
                             headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req)))   # -> {"prompt_id": ...}; poll GET /history/<prompt_id>
```

## Example: worker-comfyui style payload (RunPod)

```json
{
  "input": {
    "workflow": { "...": "contents of the .api.json with your values" },
    "images": [{ "name": "input.png", "image": "<base64 PNG/JPEG, no data: prefix>" }]
  }
}
```

The worker uploads `images[*]` into ComfyUI's `input/` folder, so node `1` can reference them by `name`.

## Notes

- **All branches are validated.** ComfyUI validates every node in the prompt, including branches that a toggle disables. All models must be installed, even for a stage you do not use.
- **Only the boolean values change between toggle states.** The graph stays the same, so a single deployment serves every combination.
- **Mask input (General Enhancement).** `LoadImage` turns the alpha channel into the mask (mask = 1 − alpha). To enhance only part of the image, send an RGBA PNG whose transparent pixels cover that area, and set node `5` to `true`. A painted mask with `5 = false` is ignored.
