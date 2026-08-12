"""Utility helpers and world-editing tools for 3DXChat building."""

from .common import coerce_path, ensure_list, normalize_name
from .ops import (
    BoundingBox,
    merge_worlds,
    move_world,
    remove_duplicates,
    replace_color,
    round_angles,
    scale_world,
    world_stats,
)
from .world import (
    count_objects,
    iter_objects,
    load_world,
    new_world,
    save_world,
)

__all__ = [
    "coerce_path",
    "ensure_list",
    "normalize_name",
    "BoundingBox",
    "merge_worlds",
    "move_world",
    "remove_duplicates",
    "replace_color",
    "round_angles",
    "scale_world",
    "world_stats",
    "count_objects",
    "iter_objects",
    "load_world",
    "new_world",
    "save_world",
]
