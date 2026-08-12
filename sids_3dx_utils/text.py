"""Render text into 3DXChat worlds using glyph font libraries.

A font is a folder containing:
    <name>.json   - metadata: spacing, line_spacing, space width, and a
                    "glyphs" map of char -> {bb, baseline, width?}
    <name>.world  - a world file containing the built glyph geometry

Each glyph's "bb" is a bounding box (p/r/s) locating its objects inside the
font world. Rendering copies those objects, aligns them to a common
baseline, and advances a cursor per character.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from .world import World, WorldObject, iter_objects, load_world, new_world

Vec3 = tuple[float, float, float]


class FontError(ValueError):
    """Raised when a font library is missing or malformed."""


class Glyph:
    def __init__(self, char: str, entry: dict, objects: list[WorldObject]):
        self.char = char
        bb = entry["bb"]
        self.cell_center = list(bb["p"])
        self.cell_size = _rotated_extents(bb["s"], bb["r"])
        self.baseline = float(entry.get("baseline", bb["p"][1]))
        self.width = entry.get("width")  # optional advance override
        self.objects = objects
        xs = [o["p"][0] for o in objects]
        self.geom_mid_x = (min(xs) + max(xs)) / 2.0

    @property
    def advance(self) -> float:
        return float(self.width) if self.width else self.cell_size[0]


def _rotated_extents(size: list[float], rot: list[float]) -> list[float]:
    """World-space extents of a box rotated by multiples of 90 degrees."""
    ext = [abs(float(v)) for v in size]
    rx = round(float(rot[0])) % 360
    if rx in (90, 270):
        ext[1], ext[2] = ext[2], ext[1]
    return ext


def _cell_bounds(
    glyph_entry: dict, *, margin: tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> list[tuple[float, float]]:
    bb = glyph_entry["bb"]
    center = bb["p"]
    ext = _rotated_extents(bb["s"], bb["r"])
    return [
        (c - e / 2.0 - m, c + e / 2.0 + m)
        for c, e, m in zip(center, ext, margin)
    ]


class Font:
    """A glyph font loaded from a font folder."""

    def __init__(self, name: str, meta: dict, glyphs: dict[str, Glyph]):
        self.name = name
        self.spacing = float(meta.get("spacing", 0.4))
        self.line_spacing = float(meta.get("line_spacing", 8.0))
        self.space_width = float(meta.get("space", 1.5))
        self.meta = meta
        self.glyphs = glyphs

    @classmethod
    def load(cls, font_dir: str | Path) -> "Font":
        font_dir = Path(font_dir)
        candidates = sorted(font_dir.glob("*.json"))
        if not candidates:
            raise FontError(f"{font_dir}: no font .json found")
        meta_path = candidates[0]
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        if "glyphs" not in meta:
            raise FontError(f"{meta_path}: missing 'glyphs' map")

        world_path = font_dir / meta.get("filename", "")
        if not world_path.is_file():
            worlds = sorted(font_dir.glob("*.world"))
            if not worlds:
                raise FontError(
                    f"{font_dir}: font world file "
                    f"{meta.get('filename')!r} not found"
                )
            world_path = worlds[0]
        world = load_world(world_path)
        all_objects = list(iter_objects(world))

        # Tall glyphs (ascenders/descenders) poke out of their cells
        # vertically, so cells get a vertical margin; rows are spaced far
        # apart so this is safe. X stays strict because columns touch.
        # Each object goes to the nearest matching cell only.
        cells = {
            char: _cell_bounds(entry, margin=(1e-6, 2.0, 0.5))
            for char, entry in meta["glyphs"].items()
        }
        members: dict[str, list[WorldObject]] = {c: [] for c in cells}
        for obj in all_objects:
            pos = obj.get("p")
            if not isinstance(pos, list) or len(pos) != 3:
                continue
            best_char = None
            best_dist = None
            for char, bounds in cells.items():
                if not all(
                    lo <= pos[i] <= hi for i, (lo, hi) in enumerate(bounds)
                ):
                    continue
                bb = meta["glyphs"][char]["bb"]
                dist = (pos[0] - bb["p"][0]) ** 2 + (pos[1] - bb["p"][1]) ** 2
                if best_dist is None or dist < best_dist:
                    best_char, best_dist = char, dist
            if best_char is not None:
                members[best_char].append(obj)

        glyphs: dict[str, Glyph] = {}
        for char, entry in meta["glyphs"].items():
            if members[char]:
                glyphs[char] = Glyph(char, entry, members[char])
        if not glyphs:
            raise FontError(f"{font_dir}: no glyph geometry matched")
        return cls(font_dir.name, meta, glyphs)

    def has(self, char: str) -> bool:
        return char in self.glyphs

    def resolve(self, char: str) -> Glyph | None:
        """Find a glyph, falling back across cases."""
        for candidate in (char, char.upper(), char.lower()):
            if candidate in self.glyphs:
                return self.glyphs[candidate]
        return None


def list_fonts(fonts_root: str | Path) -> dict[str, dict]:
    """Describe every font folder under fonts_root."""
    result: dict[str, dict] = {}
    root = Path(fonts_root)
    if not root.is_dir():
        return result
    for sub in sorted(p for p in root.iterdir() if p.is_dir()):
        info: dict = {"path": str(sub)}
        try:
            font = Font.load(sub)
            info.update(
                usable=True,
                glyphs=len(font.glyphs),
                chars="".join(sorted(font.glyphs)),
            )
        except (FontError, ValueError, OSError) as exc:
            info.update(usable=False, error=str(exc))
        result[sub.name] = info
    return result


def render_text(
    font: Font,
    text: str,
    *,
    scale: float = 1.0,
    color: Vec3 | None = None,
    position: Vec3 = (0.0, 0.0, 0.0),
    align: str = "left",
) -> World:
    """Build a new world containing text rendered with font.

    Supports multi-line text (\\n). align is left, center, or right.
    Characters missing from the font (after case fallback) are skipped,
    except space which advances the cursor.
    """
    if align not in ("left", "center", "right"):
        raise ValueError("align must be left, center, or right")
    if scale <= 0:
        raise ValueError("scale must be positive")

    lines = text.split("\n")
    rendered_lines: list[tuple[list[WorldObject], float]] = []

    for line in lines:
        cursor = 0.0
        objects: list[WorldObject] = []
        for char in line:
            if char == " ":
                cursor += (font.space_width + font.spacing) * scale
                continue
            glyph = font.resolve(char)
            if glyph is None:
                continue
            advance = glyph.advance * scale
            # center the glyph geometry on its advance slot
            slot_center = cursor + advance / 2.0
            for src in glyph.objects:
                obj = copy.deepcopy(src)
                obj["p"] = [
                    (src["p"][0] - glyph.geom_mid_x) * scale + slot_center,
                    (src["p"][1] - glyph.baseline) * scale,
                    src["p"][2] * scale,
                ]
                if isinstance(obj.get("s"), list):
                    obj["s"] = [v * scale for v in obj["s"]]
                if color is not None:
                    obj["c"] = list(color)
                objects.append(obj)
            cursor += advance + font.spacing * scale
        width = max(cursor - font.spacing * scale, 0.0)
        rendered_lines.append((objects, width))

    max_width = max((w for _, w in rendered_lines), default=0.0)
    world = new_world()
    group: WorldObject = {"n": "group", "objects": []}
    for line_index, (objects, width) in enumerate(rendered_lines):
        if align == "center":
            shift = (max_width - width) / 2.0
        elif align == "right":
            shift = max_width - width
        else:
            shift = 0.0
        drop = line_index * font.line_spacing * scale
        for obj in objects:
            obj["p"] = [
                obj["p"][0] + shift + position[0],
                obj["p"][1] - drop + position[1],
                obj["p"][2] + position[2],
            ]
            group["objects"].append(obj)
    if group["objects"]:
        world["objects"].append(group)
    return world
