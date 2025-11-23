# AOSP Clang Archive

Lightweight GitHub Action that mirrors the latest Android Clang prebuilts.

## Why this project?
- Googlesource archive is capped around ~5 MB/s, so Clang downloads take forever and slow my workflows.

## How it works
```
trigger (cron/manual)
        |
  fetch latest tag
        |
  tag exists? -- yes --> stop
        |
       no
        |
 download tar.gz
        |
  publish release
        |
 send notification
```

## Download
- Go to [Github Release](https://github.com/bachnxuan/aosp_clang_mirror/releases/latest) and grab the `clang-r*.tar.gz` asset.

## Manual update
- Trigger the `Update Clang Prebuilts` workflow from the Actions tab to force a refresh.
