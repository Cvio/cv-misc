# Stand-In + VACE: Setup & Workflow Guide

**Goal:** Identity-preserving video generation using a reference image (e.g. Molly) combined
with a pose/control video, via Stand-In on top of Wan 2.1 + VACE inside ComfyUI.

**Status as of April 2026:**
- Stand-In CLI (`infer_with_vace.py`) - fully functional
- Stand-In ComfyUI preprocessor node - temporary/partial (official full node still in development)
- VACE native ComfyUI support - fully functional
- Combined Stand-In + VACE in ComfyUI - experimental, uses KJNodes as bridge

---

## Part 1 - Prerequisites

### 1.1 Environments

| Path | Purpose |
|------|---------|
| `D:\AI_Data\ai-projects\ComfyUI_windows_portable\python_embeded\python.exe` | ComfyUI's embedded Python (use for all ComfyUI installs) |
| `D:\AI_Data\ai-projects\Stand-In\.venv\Scripts\python.exe` | Stand-In CLI venv (Python 3.11, separate from ComfyUI) |

> **Key rule:** Never install Stand-In CLI dependencies into `python_embeded`.
> They require Python 3.11. ComfyUI portable uses Python 3.13. Keep them separate.
> A standard `.venv` is all you need - no conda required.

### 1.2 Custom Nodes Required (ComfyUI path)

| Node | Repo | Purpose |
|------|------|---------|
| Stand-In_Preprocessor_ComfyUI | `WeChatCV/Stand-In_Preprocessor_ComfyUI` | Official face preprocessor |
| ComfyUI-KJNodes | `kijai/ComfyUI-KJNodes` | `WanVideoAddStandInLatent` + Wan samplers |
| ComfyUI-VideoHelperSuite | `Kosinkadink/ComfyUI-VideoHelperSuite` | Load pose video, save output |

### 1.3 Models Required

| File | Destination | Notes |
|------|-------------|-------|
| `wan2.1_vace_14B_fp16.safetensors` | `models/diffusion_models/` | From `Wan-AI/Wan2.1-VACE-14B` on HF |
| `Stand-In_Wan2.1-T2V-14B_153M_v1.0.safetensors` | `models/diffusion_models/` or per Stand-In docs | From `WeChatCV/Stand-In` on HF |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders/` | Already present if using Wan 2.1 |
| `wan_2.1_vae.safetensors` | `models/vae/` | Already present if using Wan 2.1 |
| `clip_vision_h.safetensors` | `models/clip_vision/` | Already present if using Wan 2.1 I2V |

---

## Part 2 - ComfyUI Setup

All commands run from `D:\AI_Data\ai-projects\ComfyUI_windows_portable\` in Git Bash.

### 2.1 Install Stand-In Preprocessor Node

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/WeChatCV/Stand-In_Preprocessor_ComfyUI.git
cd ../..

# Install requirements (mediapipe version pin broken on Python 3.13 - skip it)
./python_embeded/python.exe -m pip install ultralytics facexlib onnxruntime-gpu
./python_embeded/python.exe -m pip install mediapipe   # without version pin
```

### 2.2 Install KJNodes (if not already present)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/kijai/ComfyUI-KJNodes.git
cd ../..
./python_embeded/python.exe -m pip install -r ComfyUI/custom_nodes/ComfyUI-KJNodes/requirements.txt
```

### 2.3 Install VideoHelperSuite

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
cd ../..
./python_embeded/python.exe -m pip install -r ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt
```

### 2.4 Download VACE Model Weights

```bash
./python_embeded/python.exe -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='Wan-AI/Wan2.1-VACE-14B',
    filename='wan2.1_vace_14B_fp16.safetensors',
    local_dir='ComfyUI/models/diffusion_models'
)
"
```

### 2.5 Download Stand-In Adapter Weights

Check the [Stand-In releases page](https://github.com/WeChatCV/Stand-In/releases) for the
current filename. As of v1.0:

```bash
./python_embeded/python.exe -c "
from huggingface_hub import hf_hub_download
# Adjust filename to match current release
hf_hub_download(
    repo_id='WeChatCV/Stand-In',
    filename='Stand-In_Wan2.1-T2V-14B_153M_v1.0.safetensors',
    local_dir='ComfyUI/models/diffusion_models'
)
"
```

### 2.6 Verify ComfyUI Starts Clean

```bash
./python_embeded/python.exe -s ComfyUI/main.py --windows-standalone-build
```

Watch for import errors on `Stand-In_Preprocessor_ComfyUI` and `ComfyUI-KJNodes`.
Both should appear in the prestartup times list without errors.

---

## Part 3 - ComfyUI Workflow (Stand-In + VACE)

### 3.1 Recommended Starting Point

Load the native VACE workflow template first and confirm it works before adding Stand-In:

1. Open ComfyUI in browser
2. Menu → Workflows → Browse Templates → Video → `Wan2.1 VACE`
3. Load it, connect your models, run a test generation

### 3.2 Workflow Architecture

```
Reference Image (Molly)
    ├─→ FaceProcessorLoader ──────────────────────────────────┐
    └─→ ApplyFaceProcessor                                    │
              │ (preprocessed face embedding)                 │
              ↓                                               │
    WanVideoAddStandInLatent  ←──────────────────────────────-┘
              │
Pose/Control Video
    └─→ VHS_LoadVideo
    └─→ VideoInputPreprocessor (pose extraction)
              │
              ↓
    WanVACEVideoEncode (VACE conditioning)
              │
              ↓
Text Prompt ──→ WanVideoTextEncode
              │
              ↓
WanVideoModelLoader (VACE weights) ──→ WanVideoSampler
                                              │
                                              ↓
                                       WanVideoDecode
                                              │
                                              ↓
                                      VHS_VideoCombine → output.mp4
```

### 3.3 Key Node Settings

**FaceProcessorLoader**
- Leave defaults initially

**ApplyFaceProcessor**
- Input: reference image of Molly (frontal, high-res recommended)
- Use general prompts: `"a woman"` not detailed descriptions - avoid over-specifying facial features

**WanVideoAddStandInLatent**
- This is the KJNodes bridge node
- Connect Stand-In embedding from `ApplyFaceProcessor` output

**WanVideoModelLoader**
- Model: `wan2.1_vace_14B_fp16.safetensors`

**WanVideoSampler**
- Steps: 20–30 to start
- CFG: 6.0
- Resolution: 480x832 or 720x1280

**VACE Scale**
- Start at `0.8` - lower this if identity is drifting toward the pose source face
- Lower values = more Stand-In identity weight, less VACE motion control

### 3.4 Important Caveats

- The KJNodes Stand-In implementation differs from the official version - expect some quality
  difference vs. the CLI route
- VACE has a built-in bias toward faces in the control video; lower `vace_scale` to counteract
- The full official Stand-In ComfyUI node is still in development - check
  `https://github.com/WeChatCV/Stand-In` for updates
- Prompt tip: do not describe Molly's appearance in the prompt - just `"a woman"` lets Stand-In
  handle identity

---

## Part 4 - CLI Route (infer_with_vace.py)

This path runs outside ComfyUI and gives the best quality. It requires a separate Python 3.11
venv because `python_embeded` runs Python 3.13 and Stand-In's dependencies require 3.11.
No conda needed - a standard venv works fine.

> **Prerequisite:** Python 3.11 must be installed on your system. Download from
> https://www.python.org/downloads/release/python-3119/ if not already present.
> Install alongside your existing Python - do not replace it.

### 4.1 Clone Stand-In and Create Venv

```bash
cd D:/AI_Data/ai-projects
git clone https://github.com/WeChatCV/Stand-In.git
cd Stand-In

# Create a 3.11 venv inside the project (using system Python 3.11 explicitly)
py -3.11 -m venv .venv
```

### 4.2 Install Dependencies

```bash
# Use full path - do not activate, consistent with your existing workflow
.venv/Scripts/python.exe -m pip install -r requirements.txt

# Optional but recommended for speed (check CUDA compatibility first)
.venv/Scripts/python.exe -m pip install flash-attn --no-build-isolation
```

### 4.3 Download Model Weights

```bash
.venv/Scripts/python.exe download_model.py
```

> If you already have `wan2.1-T2V-14B` locally, edit `download_model.py` to comment out that
> download and symlink or copy to `checkpoints/wan2.1-T2V-14B/`.

You also need VACE weights:

```bash
.venv/Scripts/python.exe -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='Wan-AI/Wan2.1-VACE-14B',
    local_dir='checkpoints/VACE'
)
"
```

### 4.4 Prepare Your Inputs

| Input | Notes |
|-------|-------|
| Reference image | Frontal face of Molly, high resolution |
| Pose/control video | Must be preprocessed using VACE's preprocessing tool before use |
| First frame image | Can be same as reference image or extracted from source video |

Preprocess the control video (required for V2V/pose control):

```bash
.venv/Scripts/python.exe preprocess_vace.py --input your_pose_video.mp4 --output test/input/pose.mp4
```

> Check the Stand-In repo for the exact preprocessing script name - it may be in a `tools/`
> or `scripts/` subdirectory.

### 4.5 Run infer_with_vace.py

All from `D:/AI_Data/ai-projects/Stand-In/`:

```bash
.venv/Scripts/python.exe infer_with_vace.py \
  --prompt "A woman raises her hands." \
  --vace_path "checkpoints/VACE/" \
  --ip_image "test/input/molly_reference.png" \
  --reference_video "test/input/pose.mp4" \
  --reference_image "test/input/molly_reference.png" \
  --output "test/output/molly_result.mp4" \
  --vace_scale 0.8
```

### 4.6 Parameter Tuning

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--vace_scale` | 0.8 | Lower = more identity, less motion fidelity. Try 0.5–0.9 |
| `--prompt` | - | Keep generic re: appearance. Describe action/scene instead |
| `--reference_video` | optional | Can omit; used for motion guidance |
| `--reference_image` | optional | Can omit; used alongside ip_image |

---

## Part 5 - Troubleshooting

### `ModuleNotFoundError: No module named 'comfy_aimdo.host_buffer'`
ComfyUI update pulled in a new dependency. Fix:
```bash
./python_embeded/python.exe -m pip install --upgrade comfy_aimdo
```

### `TypeError: Schema.__init__() got an unexpected keyword argument 'essentials_category'`
KJNodes is ahead of your ComfyUI core. Update ComfyUI:
```bash
cd ComfyUI && git pull
```

### `mediapipe<=0.10.9` install error
Requirements.txt pin is too old for Python 3.13. Skip the pin:
```bash
./python_embeded/python.exe -m pip install mediapipe
```

### `[WinError 5] Access is denied` during pip install
ComfyUI is running and has a lock on a `.pyd` file. Close ComfyUI, then retry.

### Frontend version mismatch warning
```bash
./python_embeded/python.exe -m pip install --upgrade comfyui-frontend-package
```

### Stand-In identity not holding (face drifting)
- Lower `--vace_scale` (try 0.5–0.6)
- Use a cleaner, more frontal reference image
- Remove appearance descriptions from the prompt
- Try the CLI route instead of ComfyUI for better fidelity

---

## Part 6 - Keeping Everything Updated

```bash
# Update ComfyUI core
cd D:/AI_Data/ai-projects/ComfyUI_windows_portable/ComfyUI
git pull

# Update a custom node
cd custom_nodes/Stand-In_Preprocessor_ComfyUI
git pull
cd ../ComfyUI-KJNodes
git pull
cd ../ComfyUI-VideoHelperSuite
git pull
```

Watch the Stand-In repo for the **official full ComfyUI node release** - when it drops,
replace the KJNodes bridge approach with the official nodes for best results.
`https://github.com/WeChatCV/Stand-In`
`https://github.com/WeChatCV/Stand-In_Preprocessor_ComfyUI`

---

*Last updated: April 2026*
