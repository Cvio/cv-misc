# LTX 2.3 & WAN 2.2 - LoRA Reference

## Background: Video-Reason and the VBVR dataset

Several of these links trace back to **Video-Reason** and the **VBVR dataset** (*Very Big Video Reasoning Suite*) - ~1M videos across 200 reasoning task categories focused on object trajectories, physical reasoning, causal relationships, and spatial relationships. It's the training data behind LiconStudio's VBVR releases for both LTX 2.3 and WAN 2.2.

The goal isn't flashier visuals - it's **physical and temporal coherence**: plausible object motion, consistent lighting frame-to-frame, multi-object interactions that actually make sense.

- **https://github.com/Video-Reason** - Upstream org for the dataset and training code
- **https://www.youtube.com/watch?v=wPAImw9XaW8** - Video walkthrough (likely a tutorial on using the VBVR-trained models in ComfyUI; YouTube transcripts aren't retrievable)

---

## LTX 2.3

### Official integration
**https://docs.ltx.video/open-source-model/integration-tools/comfy-ui** - Lightricks' official ComfyUI guide. Start here for model placement, workflow imports, and base T2V/I2V node setup.

### LoRAs

**LiconStudio/Ltx2.3-VBVR-lora-I2V**
https://huggingface.co/LiconStudio/Ltx2.3-VBVR-lora-I2V
- Base: `ltx-2.3-22b-dev`, rank 32, trained on ~96K videos from VBVR (240K and 480K releases planned)
- **Focus: motion physics and temporal consistency** - smoother object movement, reduced flicker, better multi-object interactions, more stable camera framing
- Good for production shots where default LTX 2.3 motion feels stiff or robotic
- License: ltx-2-community-license-agreement

**valiantcat/LTX-2.3-Transition-LORA**
https://huggingface.co/valiantcat/LTX-2.3-Transition-LORA
- Base: `Lightricks/LTX-2.3`, Apache 2.0
- Originally trained for **first-frame / last-frame transition videos** but generalizes well to T2V and I2V
- Strong at identity morphs, style transformations, scene-to-scene cuts, cinematic transitions
- **Trigger word:** `zhuanchang` (place near end of prompt)
- Settings: LoRA strength 1.0, embedded guidance 1.0, CFG 4.0
- Includes a modified Kijai-style ComfyUI workflow in the repo
- Long, descriptive temporal prompts significantly outperform keyword-only ones

---

## WAN 2.2

### Official examples
**https://comfyanonymous.github.io/ComfyUI_examples/wan22/** - Canonical ComfyUI reference for WAN 2.2 node setup, samplers, and working example workflows.

### Base models

**Wan-AI/Wan2.2-I2V-A14B**
https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B
- Official WAN 2.2 image-to-video 14B model. The foundation most WAN 2.2 LoRAs and merges are built on.

**Wan-AI/Wan2.2-Animate-14B**
https://huggingface.co/Wan-AI/Wan2.2-Animate-14B
- Character animation variant. Specialized for animating subjects rather than general I2V. Pull in as a separate tool when you have a specific use case.

### Optimized weights

**LiconStudio/VBVR-wan2.2-comfy-bf16**
https://huggingface.co/LiconStudio/VBVR-wan2.2-comfy-bf16
- **Not a LoRA** - an optimized repack of the Video-Reason VBVR-Wan2.2 fine-tune for ComfyUI
- Two versions: standard **BF16** (~27GB, 24GB+ VRAM) and **HiFi-Surgical-FP8** hybrid (~22GB, 16–24GB VRAM)
- "HiFi-Surgical" is selective quantization: they scanned all 406 linear weight tensors, kept low-SNR layers in BF16, protected outlier-heavy layers in BF16, and kept all cross-attention in blocks 30–39 in BF16. Result: ~99% reference fidelity at FP8 size
- Optimized for Blackwell (RTX 50-series) and Hopper
- Place in `ComfyUI/models/diffusion_models/`, load via CheckpointLoaderSimple or UNETLoader
- **Remote server territory, not 8GB laptop**

### Merges

**Phr00t/WAN2.2-14B-Rapid-AllInOne**
https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne
- ⚠️ **Deprecated by the author** but still widely used and functional
- FP8 all-in-one merges (WAN 2.2 + accelerators + CLIP + VAE in a single checkpoint). Load with basic ComfyUI "Load Checkpoint"
- **Run at 1 CFG and 4 steps** - these are acceleration-tuned
- MEGA variants (currently v12) handle T2V, I2V, first-to-last frame, and last-frame-only via bypass nodes
- v12 recommends `dpmpp_sde/beta`
- Compatible with WAN 2.1 LoRAs and WAN 2.2 "low noise" LoRAs (avoid "high noise" 2.2 LoRAs)
- Reports of working on 8GB VRAM, though "works" and "works well" differ
- Worth watching for a maintained successor project

---

## Cross-model prompting notes

A few patterns recur across these model cards:

- **Long, structured prompts outperform short ones.** Template: shot description → subject/scene → motion/transformation → visual details (lighting, texture, material) → atmosphere.
- **Temporal instructions matter.** Describe how things *change over time* - transformations, camera motion, object interactions - not just the end state.
- **LoRA trigger words can be missed silently.** `zhuanchang` is the explicit one here; always check LoRA cards for triggers before assuming a LoRA is underperforming.
- **CFG runs lower than image models.** valiantcat LoRA at 4.0, Phr00t merges at 1.0. High CFG over-cooks video generations and produces motion artifacts.
