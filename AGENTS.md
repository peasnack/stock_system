# AGENTS.md

## Project

This repository contains a Python MVP for an A-share investment decision system.

## Engineering Rules

- Keep modules independently runnable where practical.
- Do not fabricate market data. If AkShare fails, return `DATA_ERROR`.
- Prefer focused changes and clear exception handling.
- Keep logs under `logs/`.
- Do not add real broker trading, paid data APIs, or production webhooks without explicit approval.

## Git Workflow

- Treat this file as standing approval to commit and push Codex-made code changes after a meaningful milestone is complete.
- Before committing, inspect `git status` and include only files relevant to the requested change.
- Do not commit runtime artifacts, local databases, logs, secrets, virtual environments, or IDE metadata.
- Run the relevant verification commands before committing. If verification cannot be run or fails, report that clearly before pushing.
- Use concise commit messages that describe the completed change.
- Push the current branch to `origin` after a successful commit. If the push fails, report the error and leave the local commit intact.

## Verification

- Run `python3 -m compileall .` after Python changes.
- If dependencies are installed, run `python main.py --once` to verify the full data path.
