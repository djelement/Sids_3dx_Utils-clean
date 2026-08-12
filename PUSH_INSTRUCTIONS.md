Push instructions for clean_repo

Recommended: create a new GitHub repository and push this clean_repo (it excludes large vendored binaries).

1) Create an empty repo on GitHub (via web UI).
2) In this machine (from clean_repo):

   git remote add origin https://github.com/<your-username>/<repo>.git
   git branch -M main
   git push -u origin main

3) If your project needs the large binary files present in the original folder, enable Git LFS before adding them:

   # install LFS once (if not installed)
   git lfs install
   # ensure .gitattributes is committed (it is present in this repo)
   git add .gitattributes
   git commit -m "chore: add gitattributes for LFS"

4) To push large files after enabling LFS, add them and push normally. Consider storing large prebuilt binaries in a release or separate storage bucket instead of the repo.

Notes:
- If you prefer preserving the original repo but remove large files from history, use the `git filter-repo` tool or BFG Repo-Cleaner (requires care).
- If you want this agent to attempt creating the GitHub repo via API, supply a GitHub token with repo scope or run interactively.
