#!/usr/bin/env python3
"""
frameripper.py — Convert between video and frames.

Usage:
    python frameripper.py vtf input.mp4                        # video → frames (all)
    python frameripper.py vtf input.mp4 -o ./frames --fps 2    # 2 frames/sec
    python frameripper.py vtf input.mp4 --every 5 --format jpg # every 5th, as JPEG

    python frameripper.py ftv ./frames -o output.mp4                  # frames → video
    python frameripper.py ftv ./frames -o output.mp4 --fps 30         # custom fps
    python frameripper.py ftv ./frames -o output.mp4 --pattern "*.png" # glob pattern
    python frameripper.py ftv ./frames -o output.mp4 --codec mp4v     # custom codec

    python frameripper.py single 0 input.mp4            # first frame
    python frameripper.py single -1 input.mp4           # last frame
    python frameripper.py single -5 input.mp4           # 5th from last
    python frameripper.py single 100 input.mp4 -o thumb.jpg --format jpg
"""

import argparse
import glob
import os
import re
import sys
import time

try:
    import cv2
except ImportError:
    sys.exit("opencv-python is required.  Install with:  pip install opencv-python")


# ── Video to Frames ─────────────────────────────────────────────────────────

def video_to_frames(
    video_path: str,
    output_dir: str,
    every_n: int = 1,
    target_fps: float | None = None,
    fmt: str = "png",
    quality: int = 95,
) -> int:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        sys.exit(f"Error: cannot open '{video_path}'")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if target_fps is not None:
        every_n = max(1, round(source_fps / target_fps))

    os.makedirs(output_dir, exist_ok=True)
    pad = len(str(total_frames))

    if fmt == "jpg":
        ext, params = ".jpg", [cv2.IMWRITE_JPEG_QUALITY, quality]
    elif fmt == "webp":
        ext, params = ".webp", [cv2.IMWRITE_WEBP_QUALITY, quality]
    else:
        ext, params = ".png", [cv2.IMWRITE_PNG_COMPRESSION, 3]

    print(f"Video  : {video_path}")
    print(f"Size   : {width}x{height}  @  {source_fps:.2f} fps")
    print(f"Frames : {total_frames}  (saving every {every_n})")
    print(f"Output : {output_dir}/frame_XXXXX{ext}\n")

    saved, frame_idx = 0, 0
    t0 = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % every_n == 0:
            filepath = os.path.join(output_dir, f"frame_{frame_idx:0{pad}d}{ext}")
            cv2.imwrite(filepath, frame, params)
            saved += 1
            if saved % 100 == 0:
                print(f"  saved {saved} frames  ({time.perf_counter() - t0:.1f}s)", flush=True)
        frame_idx += 1

    cap.release()
    print(f"\nDone — {saved} frames saved in {time.perf_counter() - t0:.1f}s")
    return saved


# ── Single Frame ─────────────────────────────────────────────────────────────

def extract_single_frame(
    video_path: str,
    index: int,
    output_path: str | None = None,
    fmt: str = "png",
    quality: int = 95,
) -> str:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        sys.exit(f"Error: cannot open '{video_path}'")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Resolve negative index (Python-style)
    resolved = index if index >= 0 else total_frames + index
    if resolved < 0 or resolved >= total_frames:
        cap.release()
        sys.exit(
            f"Frame index {index} out of range. "
            f"Video has {total_frames} frames (valid: 0..{total_frames - 1} or -{total_frames}..-1)"
        )

    # Seek to the target frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, resolved)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        sys.exit(f"Error: failed to read frame {resolved}")

    # Build output path
    if fmt == "jpg":
        ext, params = ".jpg", [cv2.IMWRITE_JPEG_QUALITY, quality]
    elif fmt == "webp":
        ext, params = ".webp", [cv2.IMWRITE_WEBP_QUALITY, quality]
    else:
        ext, params = ".png", [cv2.IMWRITE_PNG_COMPRESSION, 3]

    if output_path is None:
        basename = os.path.splitext(os.path.basename(video_path))[0]
        output_path = f"{basename}_frame_{resolved}{ext}"

    cv2.imwrite(output_path, frame, params)

    timestamp = resolved / source_fps if source_fps > 0 else 0
    print(f"Video  : {video_path}  ({width}x{height} @ {source_fps:.2f} fps)")
    print(f"Total  : {total_frames} frames")
    print(f"Index  : {index}  →  frame {resolved}  ({timestamp:.3f}s)")
    print(f"Saved  : {output_path}")
    return output_path


# ── Frames to Video ─────────────────────────────────────────────────────────

def natural_sort_key(s: str):
    """Sort strings with embedded numbers naturally (frame_2 before frame_10)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]


def frames_to_video(
    frames_dir: str,
    output_path: str,
    fps: float = 30.0,
    pattern: str = "*",
    codec: str = "mp4v",
) -> int:
    # Collect image files
    search = os.path.join(frames_dir, pattern)
    candidates = sorted(glob.glob(search), key=natural_sort_key)

    # Filter to image extensions only
    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
    files = [f for f in candidates if os.path.splitext(f)[1].lower() in img_exts]

    if not files:
        sys.exit(f"No image files found matching '{search}'")

    # Read first frame to get dimensions
    sample = cv2.imread(files[0])
    if sample is None:
        sys.exit(f"Cannot read image: {files[0]}")
    height, width = sample.shape[:2]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        sys.exit(
            f"Error: VideoWriter failed to open with codec '{codec}'.\n"
            f"Try a different codec (e.g. mp4v, XVID, MJPG, avc1) or output extension."
        )

    print(f"Frames : {frames_dir}  ({len(files)} images)")
    print(f"Size   : {width}x{height}  @  {fps} fps")
    print(f"Codec  : {codec}")
    print(f"Output : {output_path}\n")

    t0 = time.perf_counter()
    written = 0

    for filepath in files:
        frame = cv2.imread(filepath)
        if frame is None:
            print(f"  warning: skipping unreadable file {filepath}")
            continue

        # Resize if dimensions don't match first frame
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height))

        writer.write(frame)
        written += 1

        if written % 100 == 0:
            print(f"  written {written} frames  ({time.perf_counter() - t0:.1f}s)", flush=True)

    writer.release()
    duration = written / fps if fps > 0 else 0
    print(f"\nDone — {written} frames → {duration:.2f}s video in {time.perf_counter() - t0:.1f}s")
    return written


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="frameripper — convert between video files and image frames.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s vtf clip.mp4                         extract all frames\n"
            "  %(prog)s vtf clip.mp4 --fps 2 --format jpg    2 fps as JPEG\n"
            "  %(prog)s ftv ./frames -o out.mp4               reassemble at 30 fps\n"
            "  %(prog)s ftv ./frames -o out.mp4 --fps 24      reassemble at 24 fps\n"
            "  %(prog)s single 0 clip.mp4                     first frame\n"
            "  %(prog)s single -1 clip.mp4                    last frame\n"
            "  %(prog)s single -5 clip.mp4                    5th from last\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── vtf (video to frames) ──
    vtf = sub.add_parser("vtf", help="Video → Frames")
    vtf.add_argument("video", help="Path to input video file")
    vtf.add_argument("-o", "--output", default=None, help="Output directory (default: <name>_frames/)")
    vtf.add_argument("--every", type=int, default=1, help="Save every Nth frame (default: 1)")
    vtf.add_argument("--fps", type=float, default=None, help="Target extraction FPS (overrides --every)")
    vtf.add_argument("--format", choices=["png", "jpg", "webp"], default="png", help="Image format (default: png)")
    vtf.add_argument("-q", "--quality", type=int, default=95, help="JPEG/WebP quality 1-100 (default: 95)")

    # ── ftv (frames to video) ──
    ftv = sub.add_parser("ftv", help="Frames → Video")
    ftv.add_argument("frames", help="Directory containing image frames")
    ftv.add_argument("-o", "--output", default="output.mp4", help="Output video path (default: output.mp4)")
    ftv.add_argument("--fps", type=float, default=30.0, help="Output video FPS (default: 30)")
    ftv.add_argument("--pattern", default="*", help="Glob pattern to match frame files (default: *)")
    ftv.add_argument("--codec", default="mp4v", help="FourCC codec (default: mp4v, try: XVID, MJPG, avc1)")

    # ── single (extract one frame) ──
    sng = sub.add_parser("single", help="Extract a single frame by index")
    sng.add_argument("index", type=int, help="Frame index (0-based). Negative = from end (-1 = last, -5 = 5th from last)")
    sng.add_argument("video", help="Path to input video file")
    sng.add_argument("-o", "--output", default=None, help="Output file path (default: <video>_frame_N.png)")
    sng.add_argument("--format", choices=["png", "jpg", "webp"], default="png", help="Image format (default: png)")
    sng.add_argument("-q", "--quality", type=int, default=95, help="JPEG/WebP quality 1-100 (default: 95)")

    args = parser.parse_args()

    if args.command == "vtf":
        if not os.path.isfile(args.video):
            sys.exit(f"File not found: {args.video}")
        output_dir = args.output or os.path.splitext(args.video)[0] + "_frames"
        video_to_frames(
            video_path=args.video,
            output_dir=output_dir,
            every_n=args.every,
            target_fps=args.fps,
            fmt=args.format,
            quality=args.quality,
        )

    elif args.command == "ftv":
        if not os.path.isdir(args.frames):
            sys.exit(f"Directory not found: {args.frames}")
        frames_to_video(
            frames_dir=args.frames,
            output_path=args.output,
            fps=args.fps,
            pattern=args.pattern,
            codec=args.codec,
        )

    elif args.command == "single":
        if not os.path.isfile(args.video):
            sys.exit(f"File not found: {args.video}")
        extract_single_frame(
            video_path=args.video,
            index=args.index,
            output_path=args.output,
            fmt=args.format,
            quality=args.quality,
        )


if __name__ == "__main__":
    main()
