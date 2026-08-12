# Sids_3dx_Utils (clean repo)

This is the curated "clean_repo" copy containing source-like files only (no large vendored binaries). Created by Copilot CLI to make starting a GitHub repository safe and lightweight.

What this copy includes
- Python/JS/TS source files, package.json, and project metadata
- No heavy binary artifacts (DLLs, EXEs, .pyd, large vendor packages)

Next recommended steps
1) Inspect and run project checks (Python tests, linters, npm builds) locally.
2) Create a GitHub repo and push this clean copy (see PUSH_INSTRUCTIONS.md).
3) If the project requires prebuilt binaries, store them in releases, artifacts storage, or use Git LFS — do not keep them in history.

Tools included
- prune_large_files.ps1 — helper to list/move/delete large files from a working folder
- .gitattributes — marks common binaries for Git LFS
- PUSH_INSTRUCTIONS.md — step-by-step push instructions

If you'd like, next actions that can be automated now:
- Run Python static checks (flake8/pylint) and unit tests (if test commands are present)
- Run `npm install` and `npm run build` in dash/labextension (requires node/npm)
- Create a GitHub repo and push this clean copy (requires token/interactive consent)
