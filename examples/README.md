# Example inputs

No sample images are included. Our production inputs are client renders under NDA, and they cannot be published. Test with your own renders, or any non-confidential architectural image.

Guidelines per workflow:

| Workflow | Good test input | Notes |
|---|---|---|
| General Enhancement | Exterior or interior render, 1500–4000 px on the long side | For a masked test, paint the area in the Load Image **Mask Editor** and enable `Toggle · Use Painted Mask`. Keep the masked area larger than ~450 px per side. |
| Pro Upscale | 800–2500 px image | ×4 output is capped at 10,240 px on the long side. Inputs under 768 px are first raised to 768 px. |
| Flux 2 Klein + RAW | A raw, untextured or lightly textured architectural render | The output keeps the exact input size. RAW works best on renders that still look "CG". |

Put input files in `ComfyUI/input/`, or upload them through the Load Image node.
