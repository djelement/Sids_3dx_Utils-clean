"""Command-line interface for 3DXChat world editing.

Usage:
    python -m sids_3dx_utils info world.world
    python -m sids_3dx_utils move world.world out.world --offset 10 0 5
    python -m sids_3dx_utils merge base.world extra.world out.world
    python -m sids_3dx_utils dedupe world.world out.world
    python -m sids_3dx_utils recolor world.world out.world \
        --old 1 0 0 --new 0 0 1 --tolerance 0.01 --lights exclude
    python -m sids_3dx_utils snap-angles world.world out.world \
        --step 90 --tolerance 2
    python -m sids_3dx_utils scale world.world out.world --factor 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ops
from .text import Font, list_fonts, render_text
from .world import load_world, save_world


def _add_bbox(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bbox",
        nargs=6,
        type=float,
        metavar=("X1", "Y1", "Z1", "X2", "Y2", "Z2"),
        help="restrict the operation to this axis-aligned box",
    )


def _bbox_from(args: argparse.Namespace) -> ops.BoundingBox | None:
    if getattr(args, "bbox", None) is None:
        return None
    b = args.bbox
    return ops.BoundingBox(b[:3], b[3:])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sids_3dx_utils",
        description="Tools for editing 3DXChat .world files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="show world statistics")
    p.add_argument("input")

    p = sub.add_parser("move", help="translate objects by an offset")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--offset", nargs=3, type=float, required=True,
                   metavar=("X", "Y", "Z"))
    _add_bbox(p)

    p = sub.add_parser("merge", help="merge a second world into the first")
    p.add_argument("base")
    p.add_argument("extra")
    p.add_argument("output")
    p.add_argument("--offset", nargs=3, type=float, default=None,
                   metavar=("X", "Y", "Z"),
                   help="offset applied to the merged-in objects")

    p = sub.add_parser("dedupe", help="remove duplicate objects")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--precision", type=int, default=4,
                   help="decimal places compared (default 4)")

    p = sub.add_parser("recolor", help="replace one color with another")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--old", nargs=3, type=float, required=True,
                   metavar=("R", "G", "B"))
    p.add_argument("--new", nargs=3, type=float, required=True,
                   metavar=("R", "G", "B"))
    p.add_argument("--tolerance", type=float, default=0.0)
    p.add_argument("--lights", choices=["include", "exclude", "only"],
                   default="include",
                   help="how light-source objects participate")
    _add_bbox(p)

    p = sub.add_parser("snap-angles", help="round rotations near a step")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--step", type=float, default=90.0)
    p.add_argument("--tolerance", type=float, default=2.0)
    _add_bbox(p)

    p = sub.add_parser("scale", help="uniformly scale the world")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--factor", type=float, required=True)
    p.add_argument("--origin", nargs=3, type=float,
                   default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"))

    p = sub.add_parser("fonts", help="list available glyph fonts")
    p.add_argument("--fonts-dir", default="fonts",
                   help="folder containing font subfolders (default: fonts)")

    p = sub.add_parser("text", help="render text into a world file")
    p.add_argument("text", help="text to render; use \\n for new lines")
    p.add_argument("output")
    p.add_argument("--font", default="arial",
                   help="font folder name (default: arial)")
    p.add_argument("--fonts-dir", default="fonts")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--color", nargs=3, type=float, default=None,
                   metavar=("R", "G", "B"))
    p.add_argument("--position", nargs=3, type=float,
                   default=[0.0, 0.0, 0.0], metavar=("X", "Y", "Z"))
    p.add_argument("--align", choices=["left", "center", "right"],
                   default="left")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "info":
        world = load_world(args.input)
        print(json.dumps(ops.world_stats(world), indent=2))
        return 0

    if args.command == "fonts":
        info = list_fonts(args.fonts_dir)
        print(json.dumps(info, indent=2))
        return 0

    if args.command == "text":
        font = Font.load(str(Path(args.fonts_dir) / args.font))
        rendered = render_text(
            font,
            args.text.replace("\\n", "\n"),
            scale=args.scale,
            color=tuple(args.color) if args.color else None,
            position=tuple(args.position),
            align=args.align,
        )
        save_world(rendered, args.output)
        from .world import count_objects
        print(
            f"rendered {count_objects(rendered)} objects with "
            f"{font.name} -> {args.output}"
        )
        return 0

    if args.command == "merge":
        base = load_world(args.base)
        extra = load_world(args.extra)
        added = ops.merge_worlds(base, extra, offset=args.offset)
        save_world(base, args.output)
        print(f"merged {added} objects -> {args.output}")
        return 0

    world = load_world(args.input)

    if args.command == "move":
        n = ops.move_world(world, args.offset, bbox=_bbox_from(args))
        message = f"moved {n} objects"
    elif args.command == "dedupe":
        n = ops.remove_duplicates(world, precision=args.precision)
        message = f"removed {n} duplicates"
    elif args.command == "recolor":
        n = ops.replace_color(
            world,
            args.old,
            args.new,
            tolerance=args.tolerance,
            lights=args.lights,
            bbox=_bbox_from(args),
        )
        message = f"recolored {n} objects"
    elif args.command == "snap-angles":
        n = ops.round_angles(
            world,
            step=args.step,
            tolerance=args.tolerance,
            bbox=_bbox_from(args),
        )
        message = f"snapped angles on {n} objects"
    elif args.command == "scale":
        n = ops.scale_world(world, args.factor, origin=args.origin)
        message = f"scaled {n} objects"
    else:  # pragma: no cover - argparse enforces choices
        return 2

    save_world(world, args.output)
    print(f"{message} -> {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
