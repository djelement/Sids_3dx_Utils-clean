"""Load, save, and traverse 3DXChat .world files.

A .world file is JSON:

    {
      "respawn":   {"p": [x, y, z], "r": angle},
      "ambient":   [ ... floats ... ],
      "oceanlevel": 0.0,
      "weather":   "Night",
      "valuetype": "float",
      "objects":   [ {object}, ... ]
    }

Each object has:
    n  - type name ("Box", "Tube", ...) or "group"
    p  - position [x, y, z]
    r  - rotation [rx, ry, rz] (degrees)
    s  - scale    [sx, sy, sz]
    c  - color    [r, g, b] (0..1 floats)

A "group" object has an "objects" list instead of p/r/s/c. 3DXChat only
supports a single level of grouping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterator

GROUP_TYPE = "group"

# Object type names that act as light sources in 3DXChat.
LIGHT_TYPES = frozenset({"Light", "PointLight", "SpotLight", "AreaLight"})

WorldObject = dict[str, Any]
World = dict[str, Any]


def load_world(path: str | Path) -> World:
    """Load a .world file into a dict."""
    text = Path(path).read_text(encoding="utf-8-sig")
    world = json.loads(text)
    if not isinstance(world, dict):
        raise ValueError(f"{path}: expected a JSON object at top level")
    world.setdefault("objects", [])
    return world


def save_world(world: World, path: str | Path) -> None:
    """Write a world dict back to disk in compact 3DXChat-compatible JSON."""
    text = json.dumps(world, separators=(",", ":"), ensure_ascii=False)
    Path(path).write_text(text, encoding="utf-8")


def new_world(**overrides: Any) -> World:
    """Create an empty world with sane defaults."""
    world: World = {
        "respawn": {"p": [0.0, 0.0, 0.0], "r": 0.0},
        "oceanlevel": 0.0,
        "weather": "Day",
        "valuetype": "float",
        "objects": [],
    }
    world.update(overrides)
    return world


def is_group(obj: WorldObject) -> bool:
    return obj.get("n") == GROUP_TYPE


def is_light(obj: WorldObject) -> bool:
    return obj.get("n") in LIGHT_TYPES


def iter_objects(
    world: World, *, include_groups: bool = False
) -> Iterator[WorldObject]:
    """Yield every object in the world, descending into groups.

    Groups themselves are only yielded when include_groups is True.
    """
    stack = list(world.get("objects", []))
    while stack:
        obj = stack.pop()
        if is_group(obj):
            if include_groups:
                yield obj
            stack.extend(obj.get("objects", []))
        else:
            yield obj


def count_objects(world: World) -> int:
    """Number of concrete (non-group) objects in the world."""
    return sum(1 for _ in iter_objects(world))


def map_objects(world: World, fn: Callable[[WorldObject], None]) -> int:
    """Apply fn to every concrete object in place. Returns objects visited."""
    count = 0
    for obj in iter_objects(world):
        fn(obj)
        count += 1
    return count


def filter_objects(
    world: World, predicate: Callable[[WorldObject], bool]
) -> int:
    """Keep only objects matching predicate. Returns number removed.

    Empty groups left behind by filtering are removed as well.
    """
    removed = 0

    def keep(objs: list[WorldObject]) -> list[WorldObject]:
        nonlocal removed
        result = []
        for obj in objs:
            if is_group(obj):
                obj["objects"] = keep(obj.get("objects", []))
                if obj["objects"]:
                    result.append(obj)
                continue
            if predicate(obj):
                result.append(obj)
            else:
                removed += 1
        return result

    world["objects"] = keep(world.get("objects", []))
    return removed
