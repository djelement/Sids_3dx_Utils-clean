# Sid's 3DX Utils

Tools for building in **3DXChat**: a Windows GUI app (frozen PyInstaller build)
plus a growing Python library and CLI for engineering `.world` files.

## What's here

| Piece | Description |
| --- | --- |
| `Sids_3dx_Utils.exe` | The original GUI tool (bounding boxes, color replace, font text, image/obj -> world, merge, move, ...) |
| `sids_3dx_utils/` | Python package: `.world` parsing + editing operations + CLI |
| `tests/` | Pytest suite for the package |
| `fonts/` | Font glyph libraries (`.world` + `.json` metadata) used for text rendering |
| `Help/` | The original tool's HTML documentation |

## The `.world` toolkit

Works on plain 3DXChat `.world` files (JSON). No dependencies beyond Python 3.11+.

```powershell
# Inspect a world
python -m sids_3dx_utils info myroom.world

# Move everything (or just a region with --bbox)
python -m sids_3dx_utils move in.world out.world --offset 10 0 5

# Merge two builds, offsetting the incoming one
python -m sids_3dx_utils merge base.world extra.world out.world --offset 100 0 0

# Remove perfectly overlapping duplicates (color ignored, like the GUI tool)
python -m sids_3dx_utils dedupe in.world out.world

# Swap a color everywhere (tolerance + light-source filtering supported)
python -m sids_3dx_utils recolor in.world out.world --old 1 0 0 --new 0 0 1 --lights exclude

# Snap almost-straight rotations to the grid
python -m sids_3dx_utils snap-angles in.world out.world --step 90 --tolerance 2

# Scale a whole build
python -m sids_3dx_utils scale in.world out.world --factor 0.5
```

Or from Python:

```python
from sids_3dx_utils import load_world, save_world, merge_worlds, world_stats

world = load_world("base.world")
print(world_stats(world))
```

## Development

```powershell
python -m pytest -q      # run tests
python -m flake8 .       # lint (vendored dirs are excluded via .flake8)
```

CI runs both on every push (`.github/workflows/python-ci.yml`).

## Repo notes

- This is the **source-only** companion of
  [Sids_3dx_Utils-rewritten](https://github.com/djelement/Sids_3dx_Utils-rewritten),
  which carries the full frozen GUI distribution (via Git LFS + release assets).
- The `Sids_3dx_Utils.exe` GUI itself is not in this repo.
- See `.github/copilot-instructions.md` for contributor/agent onboarding.