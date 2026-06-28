# AGENTS.md

## Project

This repository contains a Python MVP for an A-share investment decision system.

## Engineering Rules

- Keep modules independently runnable where practical.
- Do not fabricate market data. If AkShare fails, return `DATA_ERROR`.
- Prefer focused changes and clear exception handling.
- Keep logs under `logs/`.
- Do not add real broker trading, paid data APIs, or production webhooks without explicit approval.

## Verification

- Run `python3 -m compileall .` after Python changes.
- If dependencies are installed, run `python main.py --once` to verify the full data path.
