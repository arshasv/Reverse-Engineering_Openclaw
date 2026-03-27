# Reverse-Engineering_Openclaw

This repo contains an OpenClaw-style website analysis workflow:

- `scripts/analyze.py` crawls a site with Playwright, captures screenshots, and writes `domMap.json` and `logs.json`.
- `scripts/generate_md.py` turns that analysis output into Markdown documentation.

The original JavaScript versions are still present in `scripts/`, but the Python versions are now available and ready to use.

## Requirements

- Python 3
- `pip`
- Playwright for Python

## Setup

From the repo root:

```bash
cd /home/user/Arsha/Reverse-Engineering_Openclaw
pip install playwright
python3 -m playwright install chromium
```

## Run The Analysis Script

Dry-run mode is the default. In dry-run mode, the script hovers over controls instead of clicking them, which is safer for exploratory captures.

```bash
cd /home/user/Arsha/Reverse-Engineering_Openclaw
python3 scripts/analyze.py https://example.com
```

If you want the script to perform actual clicks instead of dry-run hover behavior:

```bash
python3 scripts/analyze.py https://example.com --dry-run=false
```

## Generate The Markdown

If `openclaw-output/domMap.json` and `openclaw-output/logs.json` already exist, you can generate the Markdown directly:

```bash
cd /home/user/Arsha/Reverse-Engineering_Openclaw
python3 scripts/generate_md.py
```

Typical workflow:

```bash
cd /home/user/Arsha/Reverse-Engineering_Openclaw
python3 scripts/analyze.py https://example.com
python3 scripts/generate_md.py
```

## Output Files

The scripts write to these locations:

- `openclaw-output/` for screenshots and JSON analysis files
- `openclaw-output/md/` for per-page Markdown files
- `functionality.md` for the combined Markdown summary at the repo root

Important files:

- `openclaw-output/domMap.json`
- `openclaw-output/logs.json`
- `functionality.md`

## Current Notes

- `scripts/analyze.py` requires the Python `playwright` package.
- `scripts/generate_md.py` only needs the JSON output files from the analysis step.
- `package.json` still points to the original JavaScript scripts, so `npm run analyze` and `npm run functionality` still use the JS versions right now.

## Python Script Usage Summary

```bash
python3 scripts/analyze.py <startUrl>
python3 scripts/analyze.py <startUrl> --dry-run=false
python3 scripts/generate_md.py
```
