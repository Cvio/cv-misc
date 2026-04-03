"""
ComfyUI Custom Node: Iterative Video Frame Extractor

Extracts frames from a video file and outputs the last frame
as a reference image for the next generation iteration.
"""

import os
import glob
import numpy as np
import torch
from pathlib import Path

try:
    import cv2
except ImportError:
    raise ImportError(
        "OpenCV is required. Install it with: pip install opencv-python"
    )


class IterativeVideoFrameExtractor:
    """
    Loads a video from disk, extracts its frames, and outputs the last frame
    as a reference image for the next iteration of video generation.
    """

    CATEGORY = "video/iterative"
    FUNCTION = "extract"
    RETURN_TYPES = ("IMAGE", "IMAGE", "INT", "INT", "INT")
    RETURN_NAMES = (
        "last_frame",
        "all_frames",
        "frame_count",
        "width",
        "height",
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Absolute path to a video file, or a directory to auto-find the latest video.",
                }),
                "frame_index": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 999999,
                    "step": 1,
                    "tooltip": "Which frame to use as the reference. -1 = last frame.",
                }),
            },
            "optional": {
                "file_pattern": ("STRING", {
                    "default": "*.mp4",
                    "multiline": False,
                    "tooltip": "Glob pattern when video_path is a directory (e.g. '*.mp4', 'output_*.avi').",
                }),
                "skip_frames": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 120,
                    "step": 1,
                    "tooltip": "Skip N frames from the end. Useful if the final frames are black/corrupt.",
                }),
                "max_frames_loaded": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 9999,
                    "step": 1,
                    "tooltip": "Cap how many frames are held in memory for all_frames output. 0 = all.",
                }),
            },
        }

    # ── Tells ComfyUI this node's output can change between runs ──
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _resolve_video_path(video_path: str, file_pattern: str) -> str:
        """
        If video_path points to a file, return it directly.
        If it points to a directory, find the most-recently-modified
        file matching file_pattern inside it.
        """
        p = Path(video_path.strip())

        if p.is_file():
            return str(p)

        if p.is_dir():
            candidates = sorted(
                p.glob(file_pattern),
                key=lambda f: f.stat().st_mtime,
            )
            if not candidates:
                raise FileNotFoundError(
                    f"No files matching '{file_pattern}' found in {p}"
                )
            chosen = candidates[-1]  # most recent
            print(f"[IterVideoExtractor] Auto-selected: {chosen.name}")
            return str(chosen)

        raise FileNotFoundError(f"Path does not exist: {p}")

    @staticmethod
    def _decode_video(path: str, max_frames: int = 0):
        """
        Read all frames from a video file into a list of numpy arrays (H,W,3) RGB uint8.
        Returns (frames_list, width, height).
        """
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # If we only need the tail, seek ahead to save memory
        start_at = 0
        if max_frames > 0 and total > max_frames:
            start_at = total - max_frames
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_at)

        frames = []
        while True:
            ret, bgr = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            frames.append(rgb)

        cap.release()

        if not frames:
            raise RuntimeError(f"Video has zero readable frames: {path}")

        print(
            f"[IterVideoExtractor] Loaded {len(frames)} frames "
            f"({width}x{height}) from {Path(path).name}"
        )
        return frames, width, height

    @staticmethod
    def _numpy_to_comfy(frames: list[np.ndarray]) -> torch.Tensor:
        """
        Convert a list of (H, W, 3) uint8 numpy arrays to a single
        ComfyUI IMAGE tensor: (B, H, W, C) float32 in [0, 1].
        """
        stacked = np.stack(frames, axis=0).astype(np.float32) / 255.0
        return torch.from_numpy(stacked)

    # ── Main execution ────────────────────────────────────────────

    def extract(
        self,
        video_path: str,
        frame_index: int = -1,
        file_pattern: str = "*.mp4",
        skip_frames: int = 0,
        max_frames_loaded: int = 0,
    ):
        resolved = self._resolve_video_path(video_path, file_pattern)
        frames, w, h = self._decode_video(resolved, max_frames_loaded)

        # Apply skip_frames (trim from the tail)
        if skip_frames > 0 and skip_frames < len(frames):
            frames = frames[: len(frames) - skip_frames]

        # Determine the reference frame
        if frame_index == -1:
            ref_idx = len(frames) - 1
        else:
            ref_idx = min(frame_index, len(frames) - 1)

        ref_frame = frames[ref_idx]

        # Build ComfyUI tensors
        last_frame_tensor = self._numpy_to_comfy([ref_frame])   # (1, H, W, 3)
        all_frames_tensor = self._numpy_to_comfy(frames)        # (B, H, W, 3)
        frame_count = len(frames)

        return (last_frame_tensor, all_frames_tensor, frame_count, w, h)


class IterativeVideoPathBuilder:
    """
    Utility node that constructs a video path with an iteration counter.
    Useful for chaining iterations in a loop: iteration 0 → video_00000.mp4,
    iteration 1 → video_00001.mp4, etc.
    """

    CATEGORY = "video/iterative"
    FUNCTION = "build_path"
    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("current_video_path", "next_video_path", "next_iteration")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_directory": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Directory where iteration videos are saved.",
                }),
                "filename_prefix": ("STRING", {
                    "default": "iter_video",
                    "multiline": False,
                }),
                "iteration": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 99999,
                    "step": 1,
                }),
                "extension": (["mp4", "avi", "mov", "webm"], {
                    "default": "mp4",
                }),
            },
        }

    def build_path(
        self,
        output_directory: str,
        filename_prefix: str,
        iteration: int,
        extension: str,
    ):
        directory = Path(output_directory.strip())
        current = directory / f"{filename_prefix}_{iteration:05d}.{extension}"
        next_iter = iteration + 1
        next_path = directory / f"{filename_prefix}_{next_iter:05d}.{extension}"

        return (str(current), str(next_path), next_iter)


# ── Node Registration ────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "IterativeVideoFrameExtractor": IterativeVideoFrameExtractor,
    "IterativeVideoPathBuilder": IterativeVideoPathBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "IterativeVideoFrameExtractor": "Iterative Video Frame Extractor",
    "IterativeVideoPathBuilder": "Iterative Video Path Builder",
}
