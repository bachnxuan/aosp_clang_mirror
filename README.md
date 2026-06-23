# AOSP Clang mirror

This repo watches for new AOSP Clang prebuilts, uploads them to GitHub Releases, and posts a Telegram message when a new one appears.

## Why this repo exists

The googlesource archive is capped around ~5 MB/s, so Clang downloads take forever and slow my workflows.

## What it does

The update job runs every 3 hours, or when you start it manually.

1. `app.py fetch` looks up the newest AOSP Clang revision, reads its metadata, and writes `metadata.json`
2. If the release tag already exists, the run stops
3. Otherwise it downloads the tarball into `toolchain/`
4. `app.py release` uploads the tarball to GitHub Releases
5. `app.py notify` sends the Telegram message

## Workflows

- `Update Clang Prebuilts`: scheduled or manual workflow for the mirror job
- `Check`: CI workflow that runs `ruff`, `basedpyright`, and `pytest`

## Local setup

This project uses `uv` and Python 3.14.

```bash
uv sync --group dev
```

If you want to run the release flow locally, set these variables first:

```bash
export GITHUB_SERVER_URL="https://github.com"
export GITHUB_REPOSITORY="<owner>/<repo>"
export TG_BOT_TOKEN="..."
export TG_CHAT_ID="..."
```

## Local commands

Fetch metadata:

```bash
uv run app.py fetch
```

Create a release from the saved metadata:

```bash
uv run app.py release
```

Send the Telegram message:

```bash
uv run app.py notify
```

Run the same checks as CI:

```bash
uv run ruff check .
uv run basedpyright
uv run pytest -q
```

## Download

The latest mirrored tarballs are here:

- <https://github.com/bachnxuan/aosp_clang_mirror/releases/latest>

## Notes

- The GitHub release step uses `gh release create`, so local runs need `gh` installed and authenticated.
- If the fetched tag already exists, the release and Telegram steps are skipped.
