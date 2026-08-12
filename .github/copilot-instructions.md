# Copilot instructions for Sids_3dx_Utils

## What this repository is

This is the **PyInstaller-frozen Windows distribution** of *Sid's 3DX Tools* (`Sids_3dx_Utils.exe`), a PyQt6 GUI app for manipulating 3DXChat `.world` files (rounding angles, replacing colors, removing duplicate objects, rendering text from fonts, image→world and OBJ→world conversion, merging/moving worlds — see `Help/Help.html`). The app's own source code is frozen inside the exe; it is **not** in this repo.

Almost everything at the repo root is the bundled runtime: vendored site-packages (`cv2/`, `IPython/`, `dash/`, `plotly/`, `skimage/`, `PyQt6/`, `jedi/`, `parso/`, `OpenGL/`, `nbformat/`, `*.dist-info/`, …), Tcl/Tk data (`_tcl_data/`, `_tk_data/`), Qt resources, and DLLs/`.pyd` files. **Never lint, refactor, or "fix" vendored directories** — treat them as opaque artifacts.

First-party, editable code is limited to:
- `sids_3dx_utils/` — small Python utility package (`normalize_name`, `coerce_path`, `ensure_list`)
- `tests/` — pytest suite for the above
- `fonts/` — font definitions used by the Font Text tool (`.world` + `.json` per font)
- `Help/` — HTML end-user documentation

## Two nested git repositories — check your cwd

| Path | Remote | Purpose |
|---|---|---|
| repo root | `djelement/Sids_3dx_Utils-rewritten` | Full distribution, history rewritten to Git LFS |
| `clean_repo/` | `djelement/Sids_3dx_Utils-clean` | Curated source-only copy (no heavy binaries) |

`clean_repo/` is an **independent git repo nested inside the root working tree**. Always confirm which repo you're in (`git rev-parse --show-toplevel`) before committing or pushing. Changes to one are never automatically reflected in the other.

## Large binaries

- Git LFS tracks `*.dll, *.exe, *.pyd, *.pak, *.dat, *.zip, *.tar.gz` (see `.gitattributes`). Fresh clones need `git lfs install` + LFS-enabled checkout.
- Files ≥ 50 MB were moved **out of the repo** to `..\vendor_binaries\` and published as release assets on the `vendor-binaries-1` release of `Sids_3dx_Utils-rewritten`. To run the exe locally, restore them to their original paths:
  - `Qt6WebEngineCore.dll` → `PyQt6\Qt6\bin\`
  - `pybind.cp311-win_amd64.pyd` → `open3d\cpu\`
  - `llvmlite.dll` → `llvmlite\binding\`
  - `cv2.pyd` → `cv2\`
- Never commit new large binaries directly; use LFS or release assets.

## Commands

Run from the repo you intend to work in (root or `clean_repo/`).

```powershell
# Full test suite
python -m pytest tests -q

# Single test
python -m pytest tests/test_common.py::test_normalize_name_trims_and_collapses_whitespace -q

# Lint (clean_repo has the tuned .flake8; copy it to root before linting there)
flake8 .
```

- CI: `.github/workflows/python-ci.yml` (windows-latest; checkout with `lfs: true`, then pytest + flake8). Known state: the root repo's CI fails on the flake8 step because the root lacks the `.flake8` excludes that `clean_repo/.flake8` has — copy that file to the root if you need root lint to pass.
- There is no build for the exe itself (no PyInstaller spec in this repo).
- `dash/labextension`: do **not** try to build it — its `prepare` script requires `jlpm` and the repo has no `src/`/`tsconfig.json`. A prebuilt tarball exists at `dash/labextension/dist/dash-jupyterlab.tgz` (extracted copy committed in `clean_repo/dash/labextension/lib/`).

## Conventions and invariants

- `tests/test_stdlib_imports.py` asserts stdlib modules (e.g. `socket`) resolve **outside** the repo root. Don't add root-level modules/packages that shadow the standard library.
- Keep `.flake8` excludes in sync when adding vendored directories; lint only applies to first-party code.
- This environment is Windows PowerShell 5.1:
  - `&&`/`||` are not valid separators — use `;` and `if ($?) { … }`.
  - `npm.ps1` is blocked by execution policy — run npm through cmd: `& $env:ComSpec /c "cd /d <dir> && npm install"`.
- `clean_repo/prune_large_files.ps1` lists/moves/deletes files above a size threshold; `clean_repo/PUSH_INSTRUCTIONS.md` documents the remote/LFS workflow.
