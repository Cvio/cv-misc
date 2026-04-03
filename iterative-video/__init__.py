"""
ComfyUI-Iterative-Video
~~~~~~~~~~~~~~~~~~~~~~~~
Custom nodes for iterative video generation workflows.
Extracts frames from a previous iteration's video and feeds
the last frame back as a reference image for the next iteration.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

WEB_DIRECTORY = None  # No custom JS widgets needed
