"""Editing operations on 3DXChat worlds.

These mirror (and extend) the features of the original Sid's 3DX Tools GUI:
move, merge, duplicate removal, color replace, angle rounding, and
bounding-box scoped edits. All functions modify the world in place and
return a count of affected objects.
"""

from __future__ import annotations

import math
from typing import Sequence

from .world import (
    World,
    WorldObject,
    is_group,
    is_light,
    iter_objects,
)

Vec3 = Sequence[float]

# How light sources participate in an operation.
LIGHTS_INCLUDE = "include"  # act on everything
LIGHTS_EXCLUDE = "exclude"  # skip light sources
LIGHTS_ONLY = "only"  # act only on light sources


def _light_filter(obj: WorldObject, lights: str) -> bool:
    if lights == LIGHTS_EXCLUDE:
        return not is_light(obj)
    if lights == LIGHTS_ONLY:
        return is_light(obj)
    return True


class BoundingBox:
    """Axis-aligned box used to scope operations to a region."""

    def __init__(self, minimum: Vec3, maximum: Vec3) -> None:
        self.min = [min(a, b) for a, b in zip(minimum, maximum)]
        self.max = [max(a, b) for a, b in zip(minimum, maximum)]

    def contains(self, point: Vec3) -> bool:
        return all(
            lo <= v <= hi for lo, v, hi in zip(self.min, point, self.max)
        )

    def contains_object(self, obj: WorldObject) -> bool:
        pos = obj.get("p")
        return pos is not None and self.contains(pos)


def move_world(world: World, offset: Vec3, *, bbox: BoundingBox | None = None) -> int:
    """Translate objects by offset. Also moves the respawn point when unscoped."""
    moved = 0
    for obj in iter_objects(world):
        if bbox is not None and not bbox.contains_object(obj):
            continue
        pos = obj.get("p")
        if pos is None:
            continue
        obj["p"] = [a + b for a, b in zip(pos, offset)]
        moved += 1
    if bbox is None:
        respawn = world.get("respawn")
        if isinstance(respawn, dict) and "p" in respawn:
            respawn["p"] = [a + b for a, b in zip(respawn["p"], offset)]
    return moved


def merge_worlds(target: World, source: World, *, offset: Vec3 | None = None) -> int:
    """Append source's objects into target, optionally offsetting them first.

    The source world is not modified. Returns objects added (groups counted
    by their contents).
    """
    import copy

    incoming = copy.deepcopy(source.get("objects", []))
    if offset is not None:
        move_world({"objects": incoming}, offset)
    target.setdefault("objects", []).extend(incoming)
    return sum(1 for _ in iter_objects({"objects": incoming}))


def remove_duplicates(world: World, *, precision: int = 4) -> int:
    """Remove objects identical in type, position, rotation, and scale.

    Color/material is deliberately ignored, matching the original tool:
    two overlapping boxes with different colors are still duplicates.
    Returns the number of objects removed.
    """
    seen: set[tuple] = set()
    removed = 0

    def key(obj: WorldObject) -> tuple:
        def r(vals):
            if isinstance(vals, list):
                return tuple(round(float(v), precision) for v in vals)
            return vals

        return (obj.get("n"), r(obj.get("p")), r(obj.get("r")), r(obj.get("s")))

    def dedupe(objs: list) -> list:
        nonlocal removed
        result = []
        for obj in objs:
            if is_group(obj):
                obj["objects"] = dedupe(obj.get("objects", []))
                if obj["objects"]:
                    result.append(obj)
                continue
            k = key(obj)
            if k in seen:
                removed += 1
            else:
                seen.add(k)
                result.append(obj)
        return result

    world["objects"] = dedupe(world.get("objects", []))
    return removed


def _color_close(a: Sequence[float], b: Sequence[float], tolerance: float) -> bool:
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def replace_color(
    world: World,
    old: Vec3,
    new: Vec3,
    *,
    tolerance: float = 0.0,
    lights: str = LIGHTS_INCLUDE,
    bbox: BoundingBox | None = None,
) -> int:
    """Replace color old with new on matching objects."""
    changed = 0
    for obj in iter_objects(world):
        if not _light_filter(obj, lights):
            continue
        if bbox is not None and not bbox.contains_object(obj):
            continue
        color = obj.get("c")
        if color is None or not _color_close(color, old, tolerance):
            continue
        obj["c"] = list(new)
        changed += 1
    return changed


def round_angles(
    world: World,
    *,
    step: float = 90.0,
    tolerance: float = 2.0,
    bbox: BoundingBox | None = None,
) -> int:
    """Snap rotation components to the nearest multiple of step.

    Only components within tolerance degrees of a multiple are snapped,
    matching the original tool's cautious behavior. Returns objects changed.
    """
    changed = 0
    for obj in iter_objects(world):
        if bbox is not None and not bbox.contains_object(obj):
            continue
        rot = obj.get("r")
        if not isinstance(rot, list):
            continue
        new_rot = list(rot)
        touched = False
        for i, angle in enumerate(rot):
            nearest = round(angle / step) * step
            if angle != nearest and abs(angle - nearest) <= tolerance:
                new_rot[i] = nearest % 360.0 if nearest % 360.0 == 0 else nearest
                touched = True
        if touched:
            obj["r"] = new_rot
            changed += 1
    return changed


def scale_world(
    world: World, factor: float, *, origin: Vec3 = (0.0, 0.0, 0.0)
) -> int:
    """Uniformly scale positions and sizes about origin."""
    if factor <= 0:
        raise ValueError("scale factor must be positive")
    changed = 0
    for obj in iter_objects(world):
        pos = obj.get("p")
        if pos is not None:
            obj["p"] = [o + (v - o) * factor for v, o in zip(pos, origin)]
        size = obj.get("s")
        if isinstance(size, list):
            obj["s"] = [v * factor for v in size]
        if pos is not None or isinstance(size, list):
            changed += 1
    return changed


def world_stats(world: World) -> dict:
    """Summary statistics: object counts by type, bounds, color count."""
    counts: dict[str, int] = {}
    colors: set[tuple] = set()
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    total = 0
    for obj in iter_objects(world):
        total += 1
        name = obj.get("n", "?")
        counts[name] = counts.get(name, 0) + 1
        color = obj.get("c")
        if isinstance(color, list):
            colors.add(tuple(round(float(v), 4) for v in color))
        pos = obj.get("p")
        if isinstance(pos, list) and len(pos) == 3:
            lo = [min(a, b) for a, b in zip(lo, pos)]
            hi = [max(a, b) for a, b in zip(hi, pos)]
    bounds = None
    if total and lo[0] is not math.inf:
        bounds = {"min": lo, "max": hi}
    return {
        "objects": total,
        "types": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "unique_colors": len(colors),
        "bounds": bounds,
    }
