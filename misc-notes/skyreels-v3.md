Welcome back! Here's everything consolidated into something you can share with your wife, plus the technical state of where we left off.

---

<br>

## Pitch: What SkyReels V3 Could Do for Content Creation

SkyReels V3 is a free, open-source AI video generator you can run locally - no monthly subscription, no per-generation fees, no cloud uploads. It's a toolkit of four related models that cover most of what a creator needs for short-form video work:

**1. Reference-to-Video (R2V) - "Put this person in that place"**
Give it a photo of a person and a photo of a background, describe the scene in words, and it generates a 5-second video of that person in that environment. Up to 3 reference images at once, so you can include a subject, a prop, and a setting. Great for branded content, mock location shoots, or character-consistent storytelling without a camera.

**2. Video Extension (V2V) - "Keep this shot going"**
Take an existing clip (phone video, stock footage, or a previously generated clip) and extend it up to 30 more seconds of natural continuation. The AI preserves motion, lighting, and character consistency. Useful for stretching B-roll, filling gaps, or building longer sequences from short source material.

**3. Shot Switching (V2V_shot) - "Cut to a new angle"**
The most cinematically interesting mode. Feed it a clip and it generates the *next shot* in the sequence - a reverse angle, cut-in, cut-away, reaction shot, or multi-angle cut - with the same characters and setting. This is essentially one-camera filmmaking with AI-generated coverage. Point a phone at something once, then get a polished multi-angle edit.

**4. Talking Avatar (A2V) - "Make this photo speak"**
Upload a portrait and an audio file (up to 200 seconds), and it animates the photo into a lip-synced talking head. Works with real people, cartoons, pets, or paintings. Multi-language support. Useful for explainer videos, virtual presenters, spokesperson content, or character dialogue without filming.

**Why this matters for content:**
- **Brand consistency** - The same character can appear across many videos without reshooting
- **Speed** - Ideas go from "concept" to "draft clip" in minutes, not a day of filming
- **Cost** - Free forever after setup. No per-video API fees
- **Privacy** - Everything runs on our own hardware, nothing uploaded to a third party
- **Creative range** - Covers reference compositing, extension, coverage, and talking heads in one toolkit

**Realistic limits to set expectations:**
- Each generation is 5-30 seconds, not feature-length
- Quality is impressive but not flawless - character faces can drift, hands can misbehave, and some prompts need multiple tries
- The 4070 laptop can run it but slowly (10-40 minutes per clip); serious work benefits from the A100 at your office
- It's a "rough draft generator" - the best workflow is using it to prototype and then cherry-picking the good takes

<br>

## To-Dos to Get Started

**Laptop (4070, 8GB VRAM) - for experimentation and smoke testing:**

1. Get one successful V2V generation running end-to-end with `SkyReelsV3_V2V_laptop_8GB_minimal_v2.json` (480×480, 49 frames). This is the "prove it works" milestone
2. Once that works, scale up one dimension at a time (resolution, then frame count) until you find your practical ceiling
3. Note the realistic runtime so we know what's feasible for overnight runs vs dinner-length runs

**Workstation (A100, 80GB VRAM) - for real quality output:**

4. Set up ComfyUI on the server (portable install + same custom node packs as laptop)
5. Install: `ComfyUI-WanVideoWrapper`, `ComfyUI-KJNodes`, `ComfyUI-VideoHelperSuite`, `ComfyUI-Custom-Scripts`, `rgthree-comfy`, `ComfyUI-ReservedVRAM`, `ComfyUI-MiniCPM`, `Comfyui_InitialB_Util`
6. Download the `V2V_shot` model (14.5 GB) - needed for `SkyReelsV3_V2VShot_A100_80GB.json`
7. Download `MiniCPM-V-4.5-int4` model for auto-prompting
8. Run the A100 workflow at full 720p to see what the model can actually do at quality

**Shared next steps (both machines):**

9. Download the fourth SkyReels model - **A2V Talking Avatar** (19.1 GB) if we want to try the talking head feature
10. Consider downloading the **Lightx2v distillation LoRA** - this speeds up sampling roughly 3x by allowing 8-step generation instead of 25
11. Collect a small library of test inputs: reference photos of the subject, some background plates, a short source video for V2V testing, and an audio clip for A2V testing
12. Circle back to the **R2V workflow** - this was your original use case (person image + background image → composited video) and we set it aside to test V2V first

<br>

## Links Used

**Main SkyReels V3 resources:**
- Official repo & docs: https://github.com/SkyworkAI/SkyReels-V3/blob/main/README.md
- Pre-quantized FP8 models (what we use in ComfyUI): https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/tree/main/SkyReelsV3
- Benji's tutorial video: https://www.youtube.com/watch?v=jI_WNV5nJ-Y

**ComfyUI custom node packs:**
- WanVideoWrapper (the core wrapper for Wan-based models): https://github.com/kijai/ComfyUI-WanVideoWrapper
- Benji's utility pack (InitialB Util): https://github.com/benjiyaya/Comfyui_InitialB_Util
- Kijai's other model repo (VAE, text encoders, clip vision): https://huggingface.co/Kijai/WanVideo_comfy

**Support files:**
- Text encoder (fp16): https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/blob/main/split_files/text_encoders/umt5_xxl_fp16.safetensors
- Text encoder (bf16, for wrapper node): https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors

<br>

## Technical State - Where We Left Off

**Machine setup:**
- Windows 11 laptop, RTX 4070 Laptop (8 GB VRAM), 32 GB system RAM
- Portable ComfyUI install at `D:\AI_Data\...`
- Python embedded 3.14, now running torch 2.10.0 with CUDA 12.6 build (we discovered CUDA 13.0 had no Windows cuDNN support)
- `python_embeded` - no venv needed, everything installs into site-packages of the embedded Python
- Remote Linux server with A100 80GB available via Docker

**Installed custom node packs:**
- ComfyUI-WanVideoWrapper ✓
- ComfyUI-KJNodes ✓
- ComfyUI-VideoHelperSuite ✓
- ComfyUI-Custom-Scripts ✓
- rgthree-comfy ✓
- ComfyUI-ReservedVRAM ✓
- ComfyUI-MiniCPM ✓
- Comfyui_InitialB_Util ✓ (required full ComfyUI stop + restart, not just UI restart)
- ComfyUI-Manager ✓
- iterative-video ✓ (your own previous custom nodes, still present)

**Downloaded models:**
- `Wan21_SkyReelsV3-R2V_fp8_scaled_mixed.safetensors` (14.5 GB) in `diffusion_models/`
- `Wan21-SkyReelsV3-V2V_fp8_scaled_mixed.safetensors` (14.5 GB) in `diffusion_models/`
- `umt5-xxl-enc-bf16.safetensors` in `text_encoders/`
- `Wan2_1_VAE_bf16.safetensors` in `vae/` (assumed - confirm)
- `clip_vision_h.safetensors` in `clip_vision/` (assumed - confirm)

**Still needed for various workflows:**
- `Wan21-SkyReelsV3-V2V_shot_fp8_scaled_mixed.safetensors` (14.5 GB) - for V2V_shot workflow
- `Wan21-SkyReelsV3-A2V_fp8_scaled_mixed.safetensors` (19.1 GB) - for Talking Avatar
- `umt5_xxl_fp16.safetensors` in `text_encoders/` - used by `WanVideoTextEncodeCached` node (different from the bf16 file)
- `wan_2.1_vae.safetensors` - newer VAE naming used in Benji workflows (may or may not be same file as the one you have)
- `MiniCPM-V-4.5-int4` - for auto-prompter in V2V_shot workflow
- `lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors` - optional distill LoRA for 3x speedup

**Gotchas we hit and solved:**
- flash_attn, Triton, and SageAttention all need to be avoided on your Windows setup - always set attention mode to `sdpa` on the model loader
- CUDA 13.0 has no Windows cuDNN support; use cu126 or cu128 torch builds
- The wrapper's `LoadWanVideoT5TextEncoder` node refuses fp8 encoder files - it wants bf16/fp16
- `WanVideoTorchCompileSettings` node must be bypassed or deleted (needs Triton which we don't have)
- WanVideoLoraSelect pointing at a missing Lightx2v LoRA needs to be bypassed
- Full ComfyUI process stop/restart is needed to register new custom nodes, not just the "Reset" button

**Workflows we built and are tracking:**

1. **`SkyReelsV3_V2V_laptop_8GB_minimal_v2.json`** - current test target. 480×480, 49 frames, block swap 40, no exotic dependencies. Last known state: was about to queue after fixing a broken model link from v1.

2. **`SkyReelsV3_V2V_laptop_8GB_minimal.json`** - v1 of the above, has the broken model link. Don't use.

3. **`SkyReelsV3_V2V_laptop_8GB.json`** - earlier version before we stripped exotic dependencies. Don't use.

4. **`SkyReelsV3_V2VShot_A100_80GB.json`** - ready to run on the A100. 1280×720, full model with MiniCPM auto-prompting. Requires V2V_shot model and MiniCPM model.

5. **`SkyReelsV3_V2V_Shot-20260303.json`** - Benji's original V2V_shot workflow, unmodified. Reference only.

6. **`SkyReels-V3-R2V-_native__20260303.json`** - Benji's R2V workflow built on native ComfyUI nodes (not wrapper). Interesting alternative for when we come back to R2V.

7. **`SkyReelsV3_TalkingAvatar-20260303.json`** - Benji's A2V workflow. Needs the A2V model downloaded to run.

8. **`skyreels_v3_r2v_reference_to_video.json`** - my earlier adaptation of the default Phantom workflow for R2V. Also waiting for later.

**Immediate next action when you sit back down:**
Load `SkyReelsV3_V2V_laptop_8GB_minimal_v2.json` onto a fresh canvas, upload a short video to `VHS_LoadVideo`, optionally edit the prompt in `WanVideoTextEncodeCached`, close other GPU-hungry apps, and hit Queue. Watch for whether it gets past the sampler OOM that killed v1.

**Deferred TODOs (don't let me forget):**
- Come back to R2V after V2V works (original use case)
- Revisit the two V2V_shot workflows once we want cinematic scene transitions
- Try A2V Talking Avatar once the A2V model is downloaded
- Explore quality-of-life workflow improvements (seed controls, multi-shot chaining via InitialB For Loops, prompt override toggles)
- Resume the linear algebra lessons toward quantum computing whenever you want a break from video stuff - we got through vectors and vector addition; scalar multiplication was next