# SkyReels V3 + ComfyUI Setup Guide

A technical walkthrough for installing SkyReels V3, its supporting tools, and the workflows we built on top of them. Aimed at someone comfortable with the command line and basic Python environments, but new to ComfyUI specifically.

Written for a fresh machine. If you already have ComfyUI installed with some custom nodes, you can skim past sections that don't apply.

---

## Table of contents

1. [What you're setting up](#what-youre-setting-up)
2. [Hardware requirements](#hardware-requirements)
3. [Prerequisites](#prerequisites)
4. [Step 1: Install ComfyUI](#step-1-install-comfyui)
5. [Step 2: Install ComfyUI Manager](#step-2-install-comfyui-manager)
6. [Step 3: Install custom node packs](#step-3-install-custom-node-packs)
7. [Step 4: Download model files](#step-4-download-model-files)
8. [Step 5: Download the MiniCPM auto-prompter (optional)](#step-5-download-the-minicpm-auto-prompter-optional)
9. [Step 6: Load a workflow and run](#step-6-load-a-workflow-and-run)
10. [Workflow reference](#workflow-reference)
11. [Running locally](#running-locally)
12. [Troubleshooting](#troubleshooting)
13. [Glossary](#glossary)
14. [All links in one place](#all-links-in-one-place)

---

## What you're setting up

By the end of this guide you'll have:

- **ComfyUI** - a node-based interface for running AI image and video models
- **ComfyUI-WanVideoWrapper** - the custom node pack that provides SkyReels V3 / Wan-family video model support
- **SkyReels V3 models** - the four diffusion models for reference-to-video, video extension, shot switching, and talking avatar
- **Supporting models** - text encoder, VAE, CLIP vision (shared across all SkyReels workflows)
- **Workflows** - JSON graph files that wire all of the above together for each use case

The total download is roughly 80–100 GB depending on which SkyReels variants you grab. Plan accordingly.

---

## Hardware requirements

SkyReels V3 is built on top of Wan 2.1, a 14B-parameter video diffusion model (the Talking Avatar variant is 19B). These are big models. Being honest about the hardware floor will save you frustration.

**Realistic tiers:**

| VRAM | Experience |
|---|---|
| **8 GB** | Not viable for SkyReels V3 in practice. The 14B attention activations exceed VRAM even with aggressive weight offloading. Works only with specialized attention kernels (SageAttention, Flash Attention) that aren't straightforward to install on Windows. |
| **12–16 GB** | Possible with SageAttention or Flash Attention installed, at low resolution (480p), short clips. Slow. |
| **24 GB** (RTX 3090, 4090, A5000) | Comfortable at 480p. Usable at 720p with block swapping. The "serious hobbyist" floor. |
| **40–48 GB** (A40, A6000, L40) | Comfortable at 720p with room for longer clips and distill LoRAs. Good workstation tier. |
| **80 GB** (A100, H100) | Full 720p, 10+ second clips, no swapping, room for auto-prompting LLMs running alongside. Ideal. |

**System RAM:** 32 GB minimum for weight offloading to work without disk thrashing. 64 GB is more comfortable.

**Storage:** 150 GB free minimum for all models, cache, and intermediate outputs. SSD strongly preferred - model loading is I/O bound.

**OS:** Linux is the preferred target. Windows works but has friction around CUDA versions, cuDNN compatibility, and optimized attention libraries (Triton, SageAttention, and Flash Attention are all painful to install on Windows). This guide notes Windows-specific gotchas where they matter.

**Decision tree:** If you have less than 24 GB VRAM, set expectations accordingly - you'll be fighting for every megabyte and the "it just runs" experience requires at least 24 GB, ideally more. Everything below assumes you're on a 24 GB+ machine.

---

## Prerequisites

Make sure you have:

- **Python 3.10, 3.11, or 3.12** - Python 3.13 and 3.14 are too new for some dependencies. The ComfyUI portable build ships with its own embedded Python, so this only matters if you're installing ComfyUI from source.
- **Git** - for cloning repositories
- **An NVIDIA GPU with current drivers** - run `nvidia-smi` to confirm it's recognized
- **CUDA toolkit 12.6 or 12.8** - CUDA 13.0 has limited ecosystem support as of this writing
- **7-Zip or equivalent** - for extracting ComfyUI portable on Windows
- **A Hugging Face account** (optional but recommended) - some repos rate-limit anonymous downloads

---

## Step 1: Install ComfyUI

**Option A: ComfyUI Portable (Windows, recommended for simplicity)**

Download the latest portable build from the ComfyUI releases page:
- https://github.com/comfyanonymous/ComfyUI/releases

Extract the `.7z` file to a drive with plenty of space (we used `D:\AI_Data\ai-projects\`). You'll end up with a folder like `ComfyUI_windows_portable` containing `ComfyUI/`, `python_embeded/`, and launcher `.bat` files.

The portable build is self-contained - it brings its own embedded Python in `python_embeded/`, so you don't need to worry about system Python versions or virtual environments. When installing Python packages, you call that embedded Python directly:

```bash
./python_embeded/python.exe -m pip install <package>
```

Do **not** create a venv inside a portable install - it'll confuse the launcher.

**Option B: ComfyUI from source (Linux, macOS, or advanced users)**

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

This gives you a regular Python environment you can manage normally.

**Verify ComfyUI runs:**

From the ComfyUI folder:

```bash
# Portable (Windows)
run_nvidia_gpu.bat

# From source
python main.py
```

You should see startup logs ending with a line like `To see the GUI go to: http://127.0.0.1:8188`. Open that URL in a browser and you should see an empty ComfyUI canvas. Close the server for now - we have more to install before it's useful.

**Links:**
- ComfyUI repo: https://github.com/comfyanonymous/ComfyUI
- ComfyUI releases: https://github.com/comfyanonymous/ComfyUI/releases

---

## Step 2: Install ComfyUI Manager

ComfyUI Manager is a custom node pack that adds a package manager to ComfyUI's UI. It's essentially mandatory - every other custom node you install will be easier with it.

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

Restart ComfyUI. You should now see a **Manager** button in the ComfyUI interface. Click it to confirm it's working.

**Link:** https://github.com/ltdrdata/ComfyUI-Manager

---

## Step 3: Install custom node packs

SkyReels V3 requires several custom node packs working together. Install all of them before moving on - partial installs will cause workflows to show red (missing) nodes when you try to load them.

**Install method:** For each pack below, you can either (a) use ComfyUI Manager's "Install Custom Nodes" search, or (b) clone the repo directly into `ComfyUI/custom_nodes/`. The Manager route is usually faster. Direct clone is shown for packs that aren't in Manager's registry.

### Required for all SkyReels workflows:

**ComfyUI-WanVideoWrapper** - the core wrapper providing all Wan-family video model nodes, including SkyReels V3 support.
- Manager search: `WanVideoWrapper`
- Direct clone: `git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git`
- Install its dependencies after cloning:
  ```bash
  ./python_embeded/python.exe -m pip install -r ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt
  ```
- Link: https://github.com/kijai/ComfyUI-WanVideoWrapper

**ComfyUI-KJNodes** - quality-of-life nodes used throughout Kijai's workflows, including `ImageResizeKJv2` which our workflows rely on.
- Manager search: `KJNodes`
- Link: https://github.com/kijai/ComfyUI-KJNodes

**ComfyUI-VideoHelperSuite** - video loading and saving (`VHS_LoadVideo`, `VHS_VideoCombine`). Required for any V2V workflow.
- Manager search: `VideoHelperSuite`
- Link: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite

### Required for Benji's workflows (if you're using them as starting points):

**ComfyUI-Custom-Scripts** - provides `ShowText|pysssss` among other utility nodes.
- Manager search: `Custom Scripts`
- Link: https://github.com/pythongosssss/ComfyUI-Custom-Scripts

**rgthree-comfy** - workflow quality-of-life (labels, muting, bookmarks, reroute improvements). Benji uses the Label nodes for workflow documentation.
- Manager search: `rgthree`
- Link: https://github.com/rgthree/rgthree-comfy

**ComfyUI-ReservedVRAM** - a small utility that reserves a buffer of VRAM for stability.
- Manager search: `ReservedVRAM`
- Link: https://github.com/BenDarDar/ComfyUI-ReservedVRAM (check Manager for the canonical source)

**Comfyui_InitialB_Util** - Benji's personal utility pack providing the `String-🔬`, `Int-🔬`, flow-control, and sigma nodes he uses in his workflows. Not available in Manager - must be cloned manually:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/benjiyaya/Comfyui_InitialB_Util.git
./python_embeded/python.exe -m pip install -r ComfyUI/custom_nodes/Comfyui_InitialB_Util/requirements.txt
```
- Link: https://github.com/benjiyaya/Comfyui_InitialB_Util

### Optional:

**ComfyUI-MiniCPM** - provides the `AILab_MiniCPM_V_Advanced` vision-language node that Benji's V2V Shot workflow uses for automatic prompt generation. Only needed if you want the "auto-prompt next shot from video" feature.
- Manager search: `MiniCPM`
- Link: https://github.com/1038lab/ComfyUI-MiniCPM

### After installing everything:

**Fully restart ComfyUI.** The UI's "Reset" or "Refresh" button does not reload custom nodes - you need a full process stop and restart. Kill the server entirely and launch it again from the command line. Verify on startup that each pack loads cleanly in the console output. Any pack that fails to import will be reported as a Python traceback.

Common import failure causes:
- Missing dependency - install requirements.txt for that pack
- Python version mismatch - the pack uses syntax or features not in your Python
- Conflict between packs - two packs registering nodes with the same name

---

## Step 4: Download model files

This is the biggest download step. Each model goes into a specific folder under `ComfyUI/models/`.

### Folder layout

Your target structure:

```
ComfyUI/models/
├── diffusion_models/     # The main SkyReels V3 models
├── vae/                  # Video variational autoencoder
├── text_encoders/        # UMT5-XXL text encoder
└── clip_vision/          # CLIP vision encoder for reference images
```

Keep everything flat inside each folder (don't create subfolders like `SkyReelsV3/`) - many workflows reference models by filename only, and subfolders cause path mismatches that force you to edit every workflow you load.

### SkyReels V3 diffusion models

All four SkyReels V3 models live in a single Hugging Face repository in pre-quantized FP8 format, ready for ComfyUI:

**Source:** https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/tree/main/SkyReelsV3

Download the model(s) you need into `ComfyUI/models/diffusion_models/`:

| Filename | Size | Use |
|---|---|---|
| `Wan21_SkyReelsV3-R2V_fp8_scaled_mixed.safetensors` | ~14.5 GB | Reference-to-Video (person + background → video) |
| `Wan21-SkyReelsV3-V2V_fp8_scaled_mixed.safetensors` | ~14.5 GB | Video extension (continue existing clip) |
| `Wan21-SkyReelsV3-V2V_shot_fp8_scaled_mixed.safetensors` | ~14.5 GB | Video shot switching (cinematic cuts) |
| `Wan21-SkyReelsV3-A2V_fp8_scaled_mixed.safetensors` | ~19.1 GB | Talking Avatar (portrait + audio → lip-synced video) |

You don't need all four to start. Pick the use case you care about most and grab that one. The others can be downloaded later.

**Download via browser:** Visit the repo URL above, click into the `SkyReelsV3/` folder, click the filename you want, then click the download icon next to the file size.

**Download via command line:**

```bash
cd ComfyUI/models/diffusion_models
wget https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/SkyReelsV3/Wan21_SkyReelsV3-R2V_fp8_scaled_mixed.safetensors
```

(The URL pattern uses `/resolve/main/` for the raw file, not `/blob/main/` which returns the HTML preview page.)

### Supporting models

These are shared across all SkyReels and Wan 2.1 workflows - download them once:

**UMT5-XXL text encoder (bf16) - required by WanVideoWrapper's text encoder nodes**

Save to `ComfyUI/models/text_encoders/`:
```
https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors
```

**UMT5-XXL text encoder (fp16) - required by Benji's workflows which use a different loader node**

Save to `ComfyUI/models/text_encoders/`:
```
https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors
```

You'll want both if you plan to run workflows from both sources. The two different node types (`LoadWanVideoT5TextEncoder` and `WanVideoTextEncodeCached`) have incompatible file format expectations. Yes, this is annoying.

**Wan 2.1 VAE**

Save to `ComfyUI/models/vae/`:
```
https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors
```

Some Benji workflows reference a filename `wan_2.1_vae.safetensors` (with dots and lowercase). If you hit a "file not found" error for that, either rename the file you have or grab the alternately-named copy from:
```
https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors
```

**CLIP vision encoder - required for reference image encoding**

Save to `ComfyUI/models/clip_vision/`:
```
https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors
```

### Optional: Lightx2v distillation LoRA

This is a step-distillation LoRA that lets the sampler produce good results in 8 steps instead of the usual 20–30, which makes generation roughly 3x faster. Strongly recommended if you can spare the disk space.

Save to `ComfyUI/models/loras/`:
```
https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors
```

When using the LoRA, drop the sampler's CFG to 1.0 and steps to 8. Without the LoRA, use CFG around 6.0 and steps around 20–25.

---

## Step 5: Download the MiniCPM auto-prompter (optional)

Benji's V2V Shot workflow uses **MiniCPM-V-4.5-int4**, a quantized vision-language model, to automatically analyze your input video and generate a cinematographic prompt for the next shot. It's a cool feature but not required - a manual-prompt version of the same workflow works without it.

If you want auto-prompting, you need to pre-stage this model **manually** rather than letting the node fetch it automatically (which it will try to do on first run). Pre-staging matters because:

- It fits the "everything runs locally, nothing phones home" principle
- The auto-download can fail partway through on slow connections
- On a local machine, auto-download isn't possible at all

**Source:** https://huggingface.co/openbmb/MiniCPM-V-4_5-int4

Note the exact repo name - it uses an **underscore** between "4" and "5", not a dot. `MiniCPM-V-4.5-int4` will 404.

**Download all 21 files in the repo** using `huggingface-cli` or a git-lfs clone:

```bash
pip install huggingface_hub
huggingface-cli download openbmb/MiniCPM-V-4_5-int4 \
  --local-dir ~/.cache/huggingface/hub/models--openbmb--MiniCPM-V-4_5-int4/snapshots/main
```

Or clone with git-lfs:

```bash
git lfs install
git clone https://huggingface.co/openbmb/MiniCPM-V-4_5-int4
```

If you cloned the git repo, move or symlink it into the Hugging Face cache directory so the transformers library can find it. The cache layout is:

```
<HF_HOME>/hub/models--openbmb--MiniCPM-V-4_5-int4/snapshots/<commit_hash>/
```

Set `HF_HOME` to control where the cache lives:

```bash
# Linux / macOS
export HF_HOME=/path/to/your/hf_cache

# Windows
set HF_HOME=D:\AI_Data\hf_cache
```

Setting `HF_HOME` before launching ComfyUI puts all downloaded models in a known location rather than the default `~/.cache/huggingface/`. Useful if your system drive is short on space.

---

## Step 6: Load a workflow and run

With everything installed and downloaded, it's time to actually run something.

### Load a workflow

ComfyUI workflows are JSON files that you drop onto the canvas. Either:
- Drag and drop the `.json` file onto the open ComfyUI tab in your browser
- Use the workflow menu: **Workflow → Open** and browse to the file

See the [Workflow reference](#workflow-reference) section below for the workflows we've prepared and what each one does.

### If nodes are red

Red nodes mean "this node class isn't registered in your ComfyUI." Two causes:
- **Missing custom node pack** - install the relevant pack and restart
- **Pack installed but failed to import** - check the ComfyUI console log on startup for Python tracebacks

ComfyUI Manager has an "Install Missing Custom Nodes" feature that detects missing node types in a loaded workflow and offers to install the packs that provide them. Use it liberally.

### Before you queue

Check a few things on the relevant nodes:

- **Model loader** points at the correct `.safetensors` file
- **VAE loader** points at your VAE file
- **Text encoder loader** - be aware of which loader the workflow uses (WanVideoWrapper's `LoadWanVideoT5TextEncoder` wants bf16; Benji's `WanVideoTextEncodeCached` wants fp16)
- **Attention mode** on the model loader - set to `sdpa` if you don't have SageAttention or Flash Attention installed
- **Any input files** - video clips, reference images, audio files - are loaded into their respective nodes

### Hit Queue

Click Queue in the ComfyUI sidebar. Watch the console for progress. Generation time depends heavily on your hardware:

- **A100 / H100:** A few minutes for a 5–10 second clip
- **RTX 4090 / 3090:** 10–20 minutes at 720p, 5–10 minutes at 480p
- **Mid-range cards:** Significantly longer, often requiring offloading tricks

---

## Workflow reference

These are the JSON workflow files we've built or adapted. Each one is a working starting point for a specific SkyReels V3 use case. They assume the folder layout and model filenames described above.

### Original workflows (unchanged reference material)

These are shipped by their respective sources without modification:

- **`wanvideo_2_1_14B_phantom_subject2vid_example_02.json`** - ships with `ComfyUI-WanVideoWrapper` in its `example_workflows/` folder. Default reference-to-video (Phantom) example. Good starting point for R2V projects.
- **`SkyReelsV3_V2V_Shot-20260303.json`** - from Benji's workflow pack. V2V shot switching with MiniCPM auto-prompting at 832×480.
- **`SkyReels-V3-R2V-_native__20260303.json`** - from Benji's pack. R2V using native ComfyUI nodes instead of WanVideoWrapper. An interesting alternative path with different characteristics.
- **`SkyReelsV3_TalkingAvatar-20260303.json`** - from Benji's pack. Talking Avatar (A2V) workflow. Requires the A2V model.

### Adapted workflows (our modifications)

**`skyreels_v3_r2v_reference_to_video.json`** - our R2V workflow adapted from the WanVideoWrapper Phantom example.

Changes we made:
- Model set to `Wan21_SkyReelsV3-R2V_fp8_scaled_mixed.safetensors`
- Attention mode: `sageattn` → `sdpa`
- `WanVideoTorchCompileSettings` node bypassed (avoids Triton dependency)
- `WanVideoLoraSelect` node bypassed (you can re-enable once you download a distill LoRA)
- Sampler steps: 8 → 25 and CFG: 1 → 6 (compensating for no distill LoRA)
- Block swap: 20 → 35 (more aggressive weight offloading)
- VAE path flattened (removed `wanvideo\` subfolder prefix)
- Unused native text-encode path bypassed

**`SkyReelsV3_V2VShot_A100_80GB.json`** - our A100-tuned adaptation of Benji's V2V Shot workflow.

Changes we made:
- Model path flattened (removed `SkyreelsV3\` subfolder prefix)
- Attention mode: `sageattn` → `sdpa` as a safe default (swap to `sageattn` or `flash_attn_2` on the A100 if those are installed - significant speedup)
- Resolution: 832×480 → 1280×720 (full HD, which SkyReels V3 was trained for)
- Sampler steps: 10 → 15
- Output saving enabled (`save_output: True`) with prefix `skyreels_v3_v2vshot_a100`

Still includes the MiniCPM auto-prompter - remove or bypass that node if you want manual prompting or don't want to download MiniCPM.

### Using your own inputs

Any of the workflows above will need you to provide the actual inputs for your generation:
- **R2V workflows:** reference images in the `LoadImage` nodes, plus a text prompt
- **V2V workflows:** a source video in the `VHS_LoadVideo` node, plus a text prompt describing the continuation
- **V2V Shot workflows:** a source video in `VHS_LoadVideo`; the MiniCPM node auto-generates the prompt if enabled
- **A2V workflows:** a portrait image in the `LoadImage` node and an audio file in the audio loader

Place your input files in `ComfyUI/input/` (that's where ComfyUI's file browsers default to) or use absolute paths.

---

## Running locally

If your target machine will be running without need for internet (or you just want to prevent any unexpected network activity during generation that may slow the process), take these extra steps:

### Before going offline

Complete all downloads on a machine with internet:
- ComfyUI and all custom node packs
- All SkyReels V3 models
- UMT5 text encoder (both variants)
- Wan 2.1 VAE
- CLIP vision
- Lightx2v LoRA (if using)
- MiniCPM-V-4_5-int4 into the HF cache directory (if using)

Verify that a full run works end-to-end on the online machine before moving everything to the offline one.

### Environment variables for offline mode

Set these before launching ComfyUI:

```bash
# Linux / macOS
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HOME=/path/to/staged/hf_cache

# Windows
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set HF_HOME=D:\AI_Data\hf_cache
```

`HF_HUB_OFFLINE=1` tells the Hugging Face library to never hit the network - it'll only look in the local cache, and will fail fast with a clear error if a model is missing rather than silently reaching out.

`TRANSFORMERS_OFFLINE=1` does the same for the transformers library specifically.

`HF_HOME` controls where cached models live. Point it at your staged cache directory.

### Auditing for unwanted network activity

Some ComfyUI custom nodes check for updates or fetch auxiliary models at import time. Before trusting a setup as fully offline, run ComfyUI on a machine with network monitoring (or simply a firewall that alerts on outbound connections) and confirm no unexpected requests fire during startup or during a generation run.

The ComfyUI Manager itself checks for registry updates on startup by default - disable that in its settings if it bothers you, or block `github.com` and `raw.githubusercontent.com` at the firewall.

---

## Troubleshooting

### Import errors on startup

**Symptom:** ComfyUI console shows a Python traceback during custom node loading.

**Causes:**
- Missing Python dependency - install the pack's `requirements.txt`
- Python version mismatch - try Python 3.11 or 3.12 if you're on 3.13+
- ComfyUI API change - the pack might use an API that your ComfyUI version doesn't provide yet (or anymore). Update both the pack and ComfyUI.

We hit this specifically with `KJNodes` on recent ComfyUI builds where `PreviewImageOrMask` failed to define its schema. Updating KJNodes through Manager usually fixes it.

### "sdpa" required because SageAttention / Flash Attention missing

**Symptom:** Model loader errors with "No module named 'sageattention'" or similar.

**Fix:** Change the `attention_mode` dropdown on the `WanVideoModelLoader` node from `sageattn` (or `flash_attn_2`) to `sdpa`. SDPA is PyTorch's built-in scaled dot product attention and is always available. It's slower than the specialized libraries but always works.

### "Invalid T5 text encoder model, fp8 scaled is not supported by this node"

**Symptom:** Text encoding fails with this error.

**Cause:** The WanVideoWrapper's `LoadWanVideoT5TextEncoder` node doesn't accept fp8 versions of the text encoder. It wants bf16 or fp16.

**Fix:** Set the model dropdown on that node to `umt5-xxl-enc-bf16.safetensors`.

### Triton not available

**Symptom:** Workflow errors out with "Cannot find a working triton installation" or similar.

**Fix:** Bypass or delete the `WanVideoTorchCompileSettings` node. Triton is required for torch.compile but not needed for actual generation. The compilation step was an optimization that you don't need for correctness.

### Out of memory at first sampling step

**Symptom:** CUDA OOM during `WanVideoSampler` execution, often on step 0.

**Causes, in order of likelihood:**
1. Your VRAM budget isn't realistic for the resolution × frame count × model size. SkyReels V3 is a 14B model and attention is O(n²) in sequence length. A 720p × 5-second clip at 14B needs about 24 GB minimum without specialized attention.
2. The text encoder is staying resident on GPU. Set the text encode node's device to `cpu` to offload it.
3. Block swap settings are too permissive. Bump `WanVideoBlockSwap` to swap more blocks (up to 40 for a 40-block model).
4. Another process is using GPU memory. Close browser tabs with hardware acceleration, other ML programs, and check `nvidia-smi`.
5. (Windows only) cuDNN memory allocator bug - try setting `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` before launching ComfyUI.

### Workflow loads with red nodes

**Symptom:** Some nodes show as red after loading a workflow.

**Cause:** A custom node pack is missing or failed to register.

**Fix:** Open ComfyUI Manager → Install Missing Custom Nodes. If a node isn't in Manager's registry (like Benji's InitialB Util), clone it manually. See the "Required custom node packs" section above.

### "Reset" doesn't register new custom nodes

**Symptom:** You installed a new custom node pack and clicked Reset in the UI, but the new nodes still aren't available.

**Fix:** The UI Reset button does not reload custom nodes. You must fully stop the ComfyUI server process and relaunch it. Kill the terminal window (or Ctrl+C the process) and start it again.

---

## Glossary

- **ComfyUI** - A node-based UI for running generative AI models. Workflows are directed graphs where nodes represent operations (load model, encode text, sample, decode, save).
- **Custom node pack** - A plugin that adds new node types to ComfyUI. Installed in `custom_nodes/`.
- **Diffusion model** - The main video generation model. Works by starting with random noise and iteratively "denoising" it guided by your text prompt.
- **VAE (Variational Autoencoder)** - The component that translates between pixel space (actual video frames) and latent space (the compact representation the diffusion model works in).
- **Text encoder** - The component that translates your text prompt into numerical embeddings the diffusion model can use. SkyReels uses UMT5-XXL.
- **CLIP vision** - The component that converts reference images into numerical embeddings, used to guide generation toward specific subjects.
- **Sampler** - The iterative denoising algorithm. Different samplers (`euler`, `dpm++_sde`, `flowmatch_pusa`, etc.) produce slightly different results and have different speed/quality tradeoffs.
- **Sampling steps** - How many denoising iterations the sampler runs. More steps generally mean higher quality, up to a point of diminishing returns. Typical range: 8 (with a distill LoRA) to 25–30 (without).
- **CFG (Classifier-Free Guidance)** - A scalar that controls how strongly the model follows your positive prompt vs. the negative prompt. Typical values: 1.0 (minimal, used with distill LoRAs) to 7.0 (strong adherence).
- **FP16 / BF16 / FP8** - Numerical precisions for storing model weights. Lower precision uses less memory but loses some accuracy. FP8 is roughly half the memory of BF16.
- **Quantization** - Storing model weights at lower precision than the original training precision. FP8-scaled models are quantized versions of the original BF16 weights.
- **LoRA (Low-Rank Adaptation)** - A small supplemental weight file that modifies the main model's behavior without changing the original. Used for character training, style adjustment, and (relevant here) step distillation.
- **Distill LoRA** - A specific kind of LoRA that lets the sampler produce good results in fewer steps. Lightx2v is an example. Major speedup at some quality cost.
- **Block swap** - A memory-saving technique where transformer blocks are kept in system RAM and loaded into VRAM on-demand during the forward pass. Trades speed for memory.
- **Attention** - The core operation inside transformer models. In video diffusion, attention memory scales roughly with the square of sequence length (which is proportional to resolution × frame count). This is usually the first thing to break when trying to fit a model into limited VRAM.
- **Flash Attention / SageAttention** - Optimized attention implementations that avoid materializing the full attention matrix in memory. Can be the difference between "OOM" and "works" on memory-constrained hardware. Hard to install on Windows.
- **Sequence length (tokens)** - The "size" of what the attention operation is processing. For video, it's roughly `(height / patch_size) × (width / patch_size) × frames`. Higher values = more memory needed.

---

## All links in one place

### Core software
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- ComfyUI releases (portable builds): https://github.com/comfyanonymous/ComfyUI/releases
- ComfyUI Manager: https://github.com/ltdrdata/ComfyUI-Manager

### Custom node packs
- ComfyUI-WanVideoWrapper (Kijai): https://github.com/kijai/ComfyUI-WanVideoWrapper
- ComfyUI-KJNodes (Kijai): https://github.com/kijai/ComfyUI-KJNodes
- ComfyUI-VideoHelperSuite (Kosinkadink): https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
- ComfyUI-Custom-Scripts (pythongosssss): https://github.com/pythongosssss/ComfyUI-Custom-Scripts
- rgthree-comfy: https://github.com/rgthree/rgthree-comfy
- ComfyUI-MiniCPM: https://github.com/1038lab/ComfyUI-MiniCPM
- Comfyui_InitialB_Util (Benji): https://github.com/benjiyaya/Comfyui_InitialB_Util

### Models
- SkyReels V3 official repo (models, docs, demos): https://github.com/SkyworkAI/SkyReels-V3
- SkyReels V3 FP8 scaled models (Kijai, ready for ComfyUI): https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/tree/main/SkyReelsV3
- Wan 2.1 supporting models (VAE, text encoders, CLIP vision, LoRAs) (Kijai): https://huggingface.co/Kijai/WanVideo_comfy
- Wan 2.1 repackaged for ComfyUI native nodes (Comfy-Org): https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged
- MiniCPM-V-4_5-int4 (for auto-prompting): https://huggingface.co/openbmb/MiniCPM-V-4_5-int4

### Tutorials and reference
- Benji's AI Playground YouTube: https://www.youtube.com/@BenjisAIPlayground
- Benji's SkyReels V3 tutorial video: https://www.youtube.com/watch?v=jI_WNV5nJ-Y
- Kijai's ComfyUI-WanVideoWrapper examples folder (in the cloned repo): `ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/example_workflows/`
