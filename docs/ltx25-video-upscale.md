# LTX 2.5 Video Upscale + CQ Enhancement

An experimental video-to-video workflow adapted from the supplied ComfyUI graph. It combines a **2× spatial latent upscale** with a low-denoise LTX 2.5 refinement pass and carries the source audio into the output. It is a separate R&D experiment; the Momi Forge parity checks for the three image workflows do not apply to it.

**Copyright © 2026 Brick Visual — original contributions.** See the [authorship and copyright notice](../workflows/ltx25-video-upscale/NOTICE.md). Third-party components and upstream material retain their respective rights and terms.

- [Editor workflow](../workflows/ltx25-video-upscale/ltx25_video_upscale.json)
- [API workflow](../workflows/ltx25-video-upscale/ltx25_video_upscale.api.json)
- [Validation and remaining limitations](validation.md#ltx-25-video-workflow)

## Setup

Use a current ComfyUI with LTX 2.5, Gemma 4, INT8 ConvRot and `ComfyMathExpression` support. The graph is checked against **ComfyUI 0.37.0 / frontend 1.53.6**; the older 0.12.3 environment used for the image workflows is insufficient.

Run these commands from the repository using ComfyUI's Python interpreter:

```bash
python scripts/install_custom_nodes.py --comfyui /path/to/ComfyUI --workflow ltx25-video-upscale
python scripts/download_models.py --comfyui /path/to/ComfyUI --workflow ltx25-video-upscale --dry-run
python scripts/download_models.py --comfyui /path/to/ComfyUI --workflow ltx25-video-upscale
```

Accept the terms on [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) and set `HF_TOKEN` before downloading its four gated files. Restart ComfyUI after installing nodes. QwenVL needs a compatible CUDA/vision build of `llama-cpp-python`, as described in the main README. VideoHelperSuite needs FFmpeg with H.264/AAC support; its requirements include `imageio-ffmpeg`.

### Custom nodes

| Pack | Nodes used | Pinned ref |
|---|---|---|
| [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | `LTXVLoopingSampler` | `ac4d998` |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | `VHS_LoadVideo`, `VHS_VideoCombine` | `993082e` |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | `GetImageSizeAndCount`, `GetImageRangeFromBatch`, `ImageBatchRepeatInterleaving`, `ImageBatchMulti` | `20a283e` |
| [ComfyUI_essentials](https://github.com/cubiq/ComfyUI_essentials) | `ImageFromBatch+` | `9d9f4be` |
| [ComfyUI-QwenVL](https://github.com/1038lab/ComfyUI-QwenVL) | `AILab_QwenVL_GGUF` | `517aed6` |

The remaining nodes are ComfyUI core. **Workflow Encrypt is not a dependency**: the pasted graph carried its registry ID on several ordinary nodes; those IDs have been corrected to their actual packs. The existing KJNodes pin already contains the four required video helpers.

### Models and exact folders

Seven files are required, about **45.8 GB / 42.7 GiB** in total; the Qwen model and projector are shared with General Enhancement and RAW Enhancement. File sizes describe disk downloads, not VRAM requirements.

| File / download | Location relative to ComfyUI |
|---|---|
| [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors) | `models/diffusion_models/` |
| [gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors) | `models/text_encoders/` |
| [ltx-2.5-video-vae-bf16.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-video-vae-bf16.safetensors) | `models/vae/` |
| [ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors) | `models/latent_upscale_models/` |
| [ltx2.5-CQ-enhancer-lora-V2.safetensors](https://huggingface.co/CQdesign/LTX-2.5-CQ-Video-and-Image-Enhancer-LoRAs/resolve/main/ltx2.5-CQ-enhancer-lora-V2.safetensors) | `models/loras/` |
| [Qwen3VL-4B-Instruct-Q8_0.gguf](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/resolve/main/Qwen3VL-4B-Instruct-Q8_0.gguf) | `models/llm/GGUF/Qwen/Qwen3-VL-4B-Instruct-GGUF/` |
| [mmproj-Qwen3VL-4B-Instruct-F16.gguf](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/resolve/main/mmproj-Qwen3VL-4B-Instruct-F16.gguf) | `models/llm/GGUF/Qwen/Qwen3-VL-4B-Instruct-GGUF/` |

Keep the filenames exactly as shown. The spatial upscaler belongs in **`latent_upscale_models`**, not `upscale_models`. These component folders also match the [Lightricks compatibility reference](https://docs.ltx.io/open-source-model/reference/workflow-asset-compatibility).

The supplied graph uses the regular **DiffVAE**. [CQdesign recommends the Conv VAE](https://huggingface.co/CQdesign/LTX-2.5-CQ-Video-and-Image-Enhancer-LoRAs) (`ltx-2.5-video-vae-conv-bf16.safetensors`) for its own enhancer workflow and says no prompt is required. This adaptation retains the supplied DiffVAE, captioning and sampling settings; equivalence to the author's V2 workflow is not claimed. If evaluating the Conv VAE, download it from Lightricks into `models/vae/` and select it at node `9`; this alternative needs its own output-quality test.

## Run in the editor

1. Open the editor JSON and upload your video at **Input Video (24 fps)**, node `29`.
2. Start with a short, non-confidential clip, for example **640×352 px**. Use dimensions divisible by 32 to avoid VAE cropping and unexpected output sizes. Set `frame_load_cap` to `49` or `97` for the first memory check; the saved value `0` processes the full clip.
3. Leave `force_rate=24`, conditioning `frame_rate=24` at node `10`, and output `frame_rate=24` at node `40`. Keep `select_every_nth=1`. Changing just the export rate changes playback speed and can desynchronize audio.
4. Run. Video is saved as H.264 MP4 (YUV420P, CRF 23) under `output/BrickVisual/`, with the prefix `LTX25_Upscale`. Source audio is included when available; no audio VAE is needed.

The `AnimateDiff` loader format is retained from the source. Here it is only a VideoHelperSuite sizing preset, not an AnimateDiff model dependency. Do not change it to `LTXV` without checking frame counts: that preset may trim frames before this graph's padding logic runs.

## Processing stages

| Stage | Nodes | What happens |
|---|---|---|
| Load | `29` | Decode the input, resample to 24 fps, keep the source audio. Starts at frame zero. |
| Pad | `53`, `63`, `64`, `65`, `66` | Count frames, repeat the last frame 1–8 times, append it so the encoded sequence has `8n+1` frames. |
| Caption | `75`, `74`, `17`, `7`, `8`, `10` | Qwen3-VL captions **only the first frame**. Gemma encodes it into the positive conditioning. The preset label “Video Summary” does not make this whole-video analysis. |
| Encode and upscale | `9`, `3`, `21`, `16`, `30`, `20` | Encode with the video VAE, spatially upscale the latents ×2, and anchor the first frame at strength 1. |
| Refine | `6`, `5`, `14`, `12`, `15`, `33`, `71` | Apply CQ Enhancer V2 at strength 1; sample with Euler ancestral, simple scheduler, 4 steps, denoise 0.15, video/audio CFG 1, fixed noise seed 42. Temporal tile size 144, overlap 48; one spatial tile. |
| Decode and trim | `26`, `70` | Tiled decode: 512 px tiles / 64 px overlap, temporal size 144 / overlap 48. Trim back to the number of frames loaded at node `29`. |
| Save | `40` | Encode at 24 fps, mux the loaded audio, and save the MP4. |

There are no stage toggles. The first-frame caption is always used; node `7`'s text is connected and its stored text widget is ignored. To supply a manual caption, disconnect that text input in the editor or replace its API link with your string. The Qwen node itself is an output node; remove it from an API prompt if you want to omit caption generation entirely.

## Changes from the pasted workflow

| Area | Supplied graph | Published graph |
|---|---|---|
| Input | A specific local video, skipping 75 frames | `input.mp4` placeholder, skipping 0 frames |
| Timing | Native input rate (`force_rate=0`), fixed 24 fps output | Input resampled to 24 fps to match conditioning/output |
| Frame padding | `max(1, ((1 - a) % 8 + 8) % 8)` | `((8 - a) % 8) + 1` |
| Output prefix | `Upscaled` | `BrickVisual/LTX25_Upscale` |
| Editor metadata | Saved previews, local output path, timing labels, incorrect pack IDs | Clean metadata, descriptive titles and setup note |
| Model and sampler choices | Supplied files and parameters | Retained, including DiffVAE, Qwen preset and denoise |

The padding correction matters when the input is already `8n+1` frames: the old expression appended one frame and broke alignment. The new expression appends eight in that case because the repeat node requires at least one repeat. All padding is removed after decode. It also gives a one-frame input at least nine encoded frames, though this workflow is intended for video.

## R&D limitations

- **Full LTX 2.5 inference has not been verified locally.** Structural checks do not establish visual quality, model compatibility at runtime, speed or a minimum VRAM requirement.
- The graph loads a full image batch and uses ordinary VAE encoding. Temporal sampling windows and tiled decoding do not make input loading or encoding stream automatically. Long or large clips can exhaust RAM/VRAM; start small.
- This is generative enhancement: fine geometry, text, faces, reflections and motion may change. The caption cannot describe action that is absent from the first frame.
- The ×2 scale applies to the VAE-aligned working dimensions. No restoration to an arbitrary original resolution or HDR/color-managed delivery is included.
- Frame trimming uses a node with a declared maximum of 4096 frames. Keep clips at or below that count, and use much shorter clips for initial testing.
- The default workflow re-encodes source audio to AAC; it does not generate new audio. Audio sync, silent inputs and temporal-window seams still need an end-to-end media test.

See [API usage](api-usage.md#ltx-25-video-upscale-workflowsltx25-video-upscaleltx25_video_upscaleapijson) for editable node IDs.
