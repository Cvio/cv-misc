# CV Toolkit — Prompt Library

A collection of prompt blueprints for generating computer vision and video/image utility scripts. Each section is self-contained — copy the section into an LLM and get a working CLI tool back.

All tools should follow these shared conventions unless stated otherwise:

- Python 3.10+ with type hints
- CLI via `argparse` with subcommands where appropriate
- Dependency on `opencv-python` primarily; `ffmpeg` subprocess calls where noted
- Progress output for batch operations
- Sensible defaults with full flag overrides
- Natural sort order for any file listings
- Clean error messages with actionable hints

---

## Table of Contents

- [Video Utilities](#video-utilities)
  - [clipper](#clipper)
  - [sidecar](#sidecar)
  - [looper](#looper)
  - [probe](#probe)
- [Image Batch Ops](#image-batch-ops)
  - [batchresize](#batchresize)
  - [gridmaker](#gridmaker)
  - [dedup](#dedup)
  - [palette](#palette)
- [Annotation & Inspection](#annotation--inspection)
  - [peeker](#peeker)
  - [diffview](#diffview)
  - [bbox2crop](#bbox2crop)
- [Format & Pipeline Glue](#format--pipeline-glue)
  - [tensor2img / img2tensor](#tensor2img--img2tensor)
  - [masktools](#masktools)
  - [gifripper](#gifripper)

---

## Video Utilities

### clipper

**Purpose:** Trim a video by timestamp or frame range without full re-encoding.

**Prompt:**

```
Write a Python CLI script called clipper.py that trims video files.

Subcommands:
  time  — trim by timestamp
  frame — trim by frame index (supports negative indexing like Python lists)

Examples:
  python clipper.py time input.mp4 00:01:30 00:02:15
  python clipper.py time input.mp4 00:01:30 00:02:15 -o trimmed.mp4
  python clipper.py frame input.mp4 100 500
  python clipper.py frame input.mp4 -300 -1

Requirements:
- Use ffmpeg via subprocess for the actual trimming (stream copy, no re-encode by default)
- Add a --reencode flag that re-encodes when precise frame-level cuts are needed
  (stream copy is fast but only cuts on keyframes)
- For frame-based trimming, use OpenCV to resolve frame indices to timestamps, then
  hand off to ffmpeg
- Validate that ffmpeg is installed and on PATH, exit with a clear message if not
- Support common formats: mp4, mkv, avi, mov, webm
- Print duration of the output clip when done
- Default output name: <input>_trimmed.<ext>
```

---

### sidecar

**Purpose:** Stitch two videos or images side-by-side or top-to-bottom for visual comparison.

**Prompt:**

```
Write a Python CLI script called sidecar.py that composites two video files or two
images into a single output for comparison.

Subcommands:
  video — stitch two videos
  image — stitch two images

Examples:
  python sidecar.py video left.mp4 right.mp4 -o compare.mp4
  python sidecar.py video left.mp4 right.mp4 --layout vertical
  python sidecar.py video left.mp4 right.mp4 --labels "Original" "Enhanced"
  python sidecar.py image a.png b.png -o diff.png --labels "Before" "After"

Requirements:
- Use OpenCV for compositing
- Layout options: horizontal (default), vertical
- If the two inputs have different resolutions, scale the smaller one to match
  (preserve aspect ratio, pad with black if needed)
- For video mode: use the shorter video's duration; match frame rates to the higher of the two
- --labels flag draws text labels (white, with dark background strip) at the top of each panel
  using cv2.putText. Auto-scale font size to panel width.
- --border flag adds a configurable pixel-width divider line between panels (default: 2px white)
- --format flag for image mode: png (default), jpg, webp
- For video output default codec is mp4v, with a --codec override flag
- Print output resolution and duration when done
```

---

### looper

**Purpose:** Create seamless loops from short video clips — useful for testing iterative generation workflows.

**Prompt:**

```
Write a Python CLI script called looper.py that takes a short video clip and creates
a looping version of it.

Subcommands:
  pingpong  — append the clip in reverse to create a bounce loop
  crossfade — blend the end into the beginning for a seamless transition
  repeat    — simple N-times repetition with no blending

Examples:
  python looper.py pingpong clip.mp4 -o loop.mp4
  python looper.py crossfade clip.mp4 -o loop.mp4 --overlap 15
  python looper.py repeat clip.mp4 -o loop.mp4 --count 4

Requirements:
- Use OpenCV for frame reading/writing
- pingpong: read all frames, write them forward then reversed (skip duplicate at the turnaround)
- crossfade: --overlap flag specifies number of frames to blend (default: 10).
  Use cv2.addWeighted to alpha-blend the last N frames with the first N frames.
  Output length = original length (the overlapping region is merged, not appended).
- repeat: straightforward concatenation, --count flag (default: 3)
- All modes support --fps override (default: match source)
- All modes support --codec flag (default: mp4v)
- Warn if the source clip has fewer frames than the crossfade overlap
- Print total output frames and duration
```

---

### probe

**Purpose:** Clean, human-readable video file info dump — resolution, fps, codec, duration, frame count, bitrate.

**Prompt:**

```
Write a Python CLI script called probe.py that prints detailed info about a video file.

Examples:
  python probe.py input.mp4
  python probe.py input.mp4 --json

Requirements:
- Use OpenCV to extract: resolution, fps, frame count, duration, codec (fourcc)
- Additionally, if ffprobe is available on PATH, run it via subprocess to get:
  bitrate, audio codec, audio sample rate, audio channels, container format,
  file size in human-readable form (MB/GB)
- Default output is a clean columnar text format like:

  File     : input.mp4
  Size     : 142.3 MB
  Format   : mp4 (H.264 / AAC)
  Duration : 00:02:34.12
  Video    : 1920x1080 @ 29.97 fps, 8547 frames
  Bitrate  : 7.2 Mbps
  Audio    : AAC 48000 Hz, stereo

- --json flag outputs all fields as a JSON object (for piping into other tools)
- If ffprobe is not available, gracefully fall back to OpenCV-only info and note
  that ffprobe would provide additional detail
- Support multiple files as positional args, print info for each separated by a blank line
```

---

## Image Batch Ops

### batchresize

**Purpose:** Resize a folder of images to a target resolution with crop, pad, or letterbox options.

**Prompt:**

```
Write a Python CLI script called batchresize.py that resizes all images in a directory
to a target resolution.

Examples:
  python batchresize.py ./images 512 512
  python batchresize.py ./images 1024 1024 --mode pad --color 0,0,0
  python batchresize.py ./images 768 768 --mode crop --gravity center
  python batchresize.py ./images 512 512 --mode letterbox -o ./resized

Requirements:
- Use OpenCV for all image operations
- Positional args: input_dir, target_width, target_height
- --mode flag with options:
    stretch  — force to exact size, ignoring aspect ratio (default)
    crop     — resize so the smallest dimension fits, then center-crop the overflow
    pad      — resize so the largest dimension fits, then pad the rest
    letterbox — same as pad but explicitly named for clarity (alias)
- --gravity flag for crop mode: center (default), top, bottom, left, right
- --color flag for pad mode: fill color as R,G,B (default: 0,0,0 black)
- --format flag: png (default), jpg, webp. Converts all output to this format.
- -o/--output flag: output directory (default: <input_dir>_resized/)
- -q/--quality flag: JPEG/WebP quality (default: 95)
- Recursive flag --recursive/-r to process subdirectories, preserving folder structure
- Skip non-image files silently
- Print progress: "Resized 45/120 images..."
- Print summary when done: count, output dir, target size
- Supported input formats: png, jpg, jpeg, webp, bmp, tiff
```

---

### gridmaker

**Purpose:** Tile N images into a contact sheet / grid with optional labels and configurable layout.

**Prompt:**

```
Write a Python CLI script called gridmaker.py that assembles multiple images into a
grid/contact sheet.

Examples:
  python gridmaker.py ./images -o grid.png
  python gridmaker.py ./images -o grid.png --cols 4 --size 256
  python gridmaker.py ./images -o grid.png --labels filename --padding 10
  python gridmaker.py img1.png img2.png img3.png -o grid.png

Requirements:
- Use OpenCV for image operations (and optionally cv2.putText for labels)
- Accept either a directory path OR multiple individual file paths as positional args
- --cols flag: number of columns (default: auto, based on sqrt of image count)
- --size flag: resize each thumbnail to NxN pixels before tiling (default: 256)
- --padding flag: pixels of padding between cells and around border (default: 4)
- --bg flag: background color as R,G,B (default: 0,0,0)
- --labels flag with options:
    none     — no labels (default)
    filename — overlay the filename at the bottom of each cell
    index    — overlay the 0-based index number
- Label rendering: white text on semi-transparent dark strip at bottom of each cell
- --format flag: output format png (default), jpg, webp
- Natural sort order for files
- Print: grid dimensions (e.g. "4x3 grid"), cell size, total images, output path
- If the last row is incomplete, leave empty cells as the background color
```

---

### dedup

**Purpose:** Find and flag duplicate or near-duplicate images using perceptual hashing.

**Prompt:**

```
Write a Python CLI script called dedup.py that finds duplicate or near-duplicate images
in a directory.

Examples:
  python dedup.py ./images
  python dedup.py ./images --threshold 5 --action move --dupes-dir ./duplicates
  python dedup.py ./images --threshold 0 --action list
  python dedup.py ./images --action symlink --dupes-dir ./dupes

Requirements:
- Use OpenCV for image loading and resize
- Implement perceptual hashing (pHash): resize to 32x32 grayscale, apply DCT,
  take top-left 8x8, compute median, generate 64-bit hash from above/below median.
  Do NOT require any external hashing library — implement it from scratch with numpy.
- --threshold flag: Hamming distance threshold for "duplicate" (default: 5, exact=0)
- --action flag:
    list   — print duplicate groups to stdout (default)
    move   — move duplicates to --dupes-dir (keep the first file in each group)
    delete — delete duplicates (keep the first in each group). Require --confirm flag.
    symlink — replace duplicates with symlinks to the kept original
- --dupes-dir flag: where to move duplicates (default: <input>_duplicates/)
- --recursive/-r flag to scan subdirectories
- For each duplicate group, keep the file with the shortest path (or first alphabetically)
- Print summary: total scanned, unique images, duplicate groups found, total duplicates
- Print each group like:
    Group 1 (3 images, distance 2):
      KEEP   img_001.png
      DUPE   img_001_copy.png
      DUPE   img_001(1).png
```

---

### palette

**Purpose:** Extract dominant colors from an image or batch of images.

**Prompt:**

```
Write a Python CLI script called palette.py that extracts dominant colors from images.

Examples:
  python palette.py photo.jpg
  python palette.py photo.jpg --colors 8
  python palette.py ./images --format json
  python palette.py photo.jpg --swatch palette.png

Requirements:
- Use OpenCV for image loading and color space conversion
- Implement K-means clustering (use cv2.kmeans, NOT sklearn) to find dominant colors
- Accept a single image or a directory of images
- --colors/-n flag: number of dominant colors to extract (default: 5)
- Default output: print colors as HEX and RGB to stdout with their percentage weight:
    #2A4858  ( 42, 72, 88)  34.2%
    #C4956A  (196,149,106)  22.8%
    ...
- --format flag: text (default), json, csv
- --swatch flag: render a visual swatch image showing the palette as colored blocks
  with hex labels, save to the given path. Each color block is proportional to its weight.
  Swatch should be a horizontal strip, e.g. 600x80 pixels.
- For directory input, process each image and output palettes separated by filename headers
- --sort flag: weight (default, most dominant first), hue, brightness
- Convert to RGB from BGR (OpenCV default) before output
```

---

## Annotation & Inspection

### peeker

**Purpose:** Quick terminal image preview without leaving the CLI — renders thumbnails inline using terminal image protocols.

**Prompt:**

```
Write a Python CLI script called peeker.py that displays image previews directly in the
terminal.

Examples:
  python peeker.py photo.jpg
  python peeker.py ./images
  python peeker.py photo.jpg --width 80
  python peeker.py ./images --cols 3

Requirements:
- Detect terminal image support and use the best available protocol:
    1. Kitty graphics protocol (best quality) — detect via TERM_PROGRAM or query
    2. iTerm2 inline images protocol — detect via TERM_PROGRAM
    3. Sixel — detect via TERM or DA1 query
    4. Fallback: ASCII/block character art using half-block characters (▀▄█) for
       a rough but readable preview. This should always work.
- Use OpenCV to load and resize images
- --width flag: thumbnail width in terminal columns (default: 60)
- For directory input, display thumbnails in a grid with filenames below each
- --cols flag: grid columns for directory mode (default: 2)
- Print image info below each preview: filename, resolution, file size
- Support png, jpg, jpeg, webp, bmp, tiff
- Keep it lightweight — no dependencies beyond opencv-python and standard library
- Note at the top of the script which terminals support which protocols
```

---

### diffview

**Purpose:** Pixel-level diff between two images, output as a heatmap highlighting changes.

**Prompt:**

```
Write a Python CLI script called diffview.py that generates a visual diff between two images.

Examples:
  python diffview.py original.png modified.png
  python diffview.py a.png b.png -o diff.png
  python diffview.py a.png b.png --mode overlay --opacity 0.5
  python diffview.py a.png b.png --threshold 10

Requirements:
- Use OpenCV for all image operations
- If images differ in size, resize the second to match the first (with a warning)
- --mode flag:
    heatmap  — absolute difference converted to a colormap (default). Use cv2.applyColorMap
               with COLORMAP_JET. Pure black = no difference, bright red = max difference.
    overlay  — semi-transparent overlay of the diff on top of the original
    side     — three-panel output: original | modified | diff heatmap
    binary   — black and white mask: white where any pixel differs beyond threshold
- --threshold flag: ignore differences below this per-channel value (default: 0)
  Useful for ignoring compression artifacts.
- --colormap flag: JET (default), HOT, INFERNO, VIRIDIS — maps to cv2 colormap constants
- -o/--output flag: output path (default: diff_output.png)
- Print summary stats:
    Changed pixels : 14,203 / 2,073,600 (0.68%)
    Max difference : 187
    Mean difference: 3.4
    PSNR           : 42.3 dB
- --format flag: png (default), jpg, webp
```

---

### bbox2crop

**Purpose:** Crop regions from images using bounding box coordinates or annotation files.

**Prompt:**

```
Write a Python CLI script called bbox2crop.py that crops bounding box regions from images.

Subcommands:
  manual — crop from explicit coordinates
  yolo   — crop from YOLO format annotation files
  coco   — crop from a COCO JSON annotation file

Examples:
  python bbox2crop.py manual image.jpg 100,50,400,300 -o crop.png
  python bbox2crop.py manual image.jpg 100,50,400,300 200,100,500,350 -o ./crops/
  python bbox2crop.py yolo ./images ./labels -o ./crops
  python bbox2crop.py coco ./images annotations.json -o ./crops
  python bbox2crop.py coco ./images annotations.json -o ./crops --categories person,car

Requirements:
- Use OpenCV for image loading and cropping
- manual mode:
    Accept one or more bounding boxes as x1,y1,x2,y2 (pixel coordinates, top-left to bottom-right)
    If one box and -o is a filename, save directly. If multiple boxes or -o is a directory,
    save as <image>_crop_0.png, <image>_crop_1.png, etc.
- yolo mode:
    Read YOLO .txt files (one per image, same stem name) from a labels directory.
    YOLO format: class_id center_x center_y width height (all normalized 0-1).
    Convert to pixel coords using image dimensions.
    --classes flag to filter by class ID (comma-separated).
- coco mode:
    Parse a COCO-format JSON file. Match annotations to images by image_id.
    --categories flag to filter by category name.
    Bounding box in COCO is [x, y, width, height] in pixels.
- All modes:
    --padding flag: expand each crop by N pixels on all sides (default: 0), clamp to image bounds
    --min-size flag: skip crops smaller than NxN pixels (default: 0, no filter)
    Output naming: <original_name>_crop_<index>_<class>.png
    Print: total images processed, total crops saved
```

---

## Format & Pipeline Glue

### tensor2img / img2tensor

**Purpose:** Convert between raw tensor dumps (.npy, .pt) and standard image formats for visual inspection.

**Prompt:**

```
Write a Python CLI script called tensorimg.py that converts between tensor files and images.

Subcommands:
  toimg   — tensor file (.npy or .pt) → image file
  totensor — image file → tensor file (.npy or .pt)

Examples:
  python tensorimg.py toimg output.npy -o preview.png
  python tensorimg.py toimg output.pt -o preview.png --layout chw
  python tensorimg.py toimg output.npy -o preview.png --normalize
  python tensorimg.py totensor photo.jpg -o input.npy
  python tensorimg.py totensor photo.jpg -o input.pt --layout chw --dtype float32

Requirements:
- For .npy files: use numpy (always available)
- For .pt files: use torch — if not installed, exit with a clear install message.
  Load with torch.load(path, map_location="cpu", weights_only=True)
- toimg mode:
    Auto-detect tensor shape and infer layout:
      (H, W)       → grayscale
      (H, W, 3)    → HWC RGB
      (H, W, 4)    → HWC RGBA
      (3, H, W)    → CHW RGB
      (4, H, W)    → CHW RGBA
      (1, C, H, W) → batched, take first item
      (B, C, H, W) → batched, save each or take --index N
    --layout flag to force: hwc or chw (override auto-detect)
    --normalize flag: if tensor values are in [0,1] scale to [0,255].
      Auto-detect: if max value <= 1.0 and dtype is float, normalize automatically.
    --colorspace flag: rgb (default), bgr — controls channel order interpretation
    --index flag: for batched tensors, which batch item to export (default: 0)
- totensor mode:
    Load image with OpenCV, convert BGR→RGB
    --layout flag: hwc (default) or chw
    --dtype flag: float32 (default), float16, uint8
    --normalize flag: scale 0-255 → 0.0-1.0 (default: true for float dtypes)
    --format flag: npy (default) or pt
- Print tensor shape, dtype, value range (min/max) for both directions
```

---

### masktools

**Purpose:** Combine, invert, threshold, and colorize binary masks — constant need in segmentation and inpainting pipelines.

**Prompt:**

```
Write a Python CLI script called masktools.py for manipulating binary/grayscale mask images.

Subcommands:
  invert    — invert a mask (255 - pixel)
  threshold — convert grayscale to binary at a threshold
  combine   — merge multiple masks with boolean operations
  colorize  — overlay a colored mask onto a base image
  info      — print mask statistics

Examples:
  python masktools.py invert mask.png -o inverted.png
  python masktools.py threshold mask.png 128 -o binary.png
  python masktools.py combine mask1.png mask2.png --op union -o merged.png
  python masktools.py combine mask1.png mask2.png --op subtract -o diff.png
  python masktools.py colorize base.jpg mask.png -o overlay.png --color 255,0,0 --opacity 0.4
  python masktools.py info mask.png

Requirements:
- Use OpenCV for all operations
- All inputs are loaded as grayscale
- invert: straightforward 255 - pixel value
- threshold:
    Positional arg for threshold value (0-255)
    --method flag: binary (default), otsu (ignore threshold value, auto-compute), adaptive
    Output is strict black/white (0 or 255)
- combine:
    Accept 2+ mask files as positional args
    --op flag: union (OR, default), intersect (AND), subtract (first minus rest), xor
    All masks resized to match the first mask's dimensions if they differ
- colorize:
    Overlay mask region onto a base image with a given color and opacity
    --color flag: R,G,B (default: 255,0,0 red)
    --opacity flag: 0.0-1.0 (default: 0.5)
    Mask white regions get the colored overlay; black regions show the base image unchanged
- info:
    Print: dimensions, unique values, coverage (% of white pixels), bounding box of
    the masked region (top-left, bottom-right), whether it's strictly binary
- All subcommands support --format flag for output: png (default), jpg, webp
```

---

### gifripper

**Purpose:** Explode GIFs to frames or assemble frames into optimized GIFs — similar to frameripper but GIF-specific with palette and timing controls.

**Prompt:**

```
Write a Python CLI script called gifripper.py for working with animated GIFs.

Subcommands:
  explode  — GIF → individual frame images
  build    — frame images → animated GIF

Examples:
  python gifripper.py explode input.gif -o ./frames
  python gifripper.py explode input.gif -o ./frames --format png
  python gifripper.py build ./frames -o output.gif --delay 100
  python gifripper.py build ./frames -o output.gif --delay 50 --loop 0 --colors 128

Requirements:
- Use Pillow (PIL) for GIF handling — it handles GIF frame extraction and palette
  optimization much better than OpenCV for this format
- explode mode:
    Extract every frame from the GIF preserving original dimensions
    Save as PNG by default (lossless), with --format override (png, jpg, webp)
    Print: frame count, dimensions, total duration, per-frame delay if variable
    --info flag: just print frame info without extracting
- build mode:
    Read images from a directory (natural sort order)
    --delay flag: frame delay in milliseconds (default: 100)
    --loop flag: loop count, 0 = infinite (default: 0)
    --colors flag: max colors in palette, 2-256 (default: 256)
    --dither flag: enable/disable dithering (default: enabled)
    --optimize flag: enable Pillow's GIF optimization (default: true)
    --resize flag: resize all frames to WxH before assembly
    Natural sort order for input files
    Print: frame count, output size in KB/MB, dimensions
- Supported image inputs for build: png, jpg, jpeg, webp, bmp
- Note: pip install Pillow if not available
```

---

## Adding New Tools

When prompting for a new tool to add to this collection, include these baseline requirements:

```
Shared conventions for all tools in this collection:
- Python 3.10+ with type hints (use X | None, not Optional[X])
- CLI via argparse
- Progress output for any batch operation processing more than ~10 items
- Natural sort order for any file listings (embedded numbers sort numerically)
- Clean error messages: validate inputs early, suggest fixes in error text
- Default output paths derived from input names (don't require -o for basic usage)
- Print a summary line when done (files processed, time elapsed, output location)
- Only hard dependency is opencv-python unless the task specifically needs another lib
- Shebang line: #!/usr/bin/env python3
- Module docstring with usage examples
```
