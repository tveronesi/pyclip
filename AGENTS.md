# AGENTS.md

## Project

Single-file Python CLI (`clip.py`) that extracts audio/video clips from YouTube videos by timestamps. Runs exclusively via Docker.

## Build & Run

```bash
# always use WSL , BASH  
docker build -t pyclip .
docker run --rm -v $(pwd):/output pyclip <URL> <TIMESTAMP> <OUTPUT> [TIMESTAMP OUTPUT ...]
```

Docker caches each stage independently — the `base` stage (Python + ffmpeg) is only rebuilt when its instructions change, so code-only changes skip the slow `apt-get install`.

No `pip install` or `uv` locally — install only happens inside the Docker image. There are no dev dependencies, tests, linter, or CI workflows.

## Architecture

- `clip.py` — entire application (~300 lines). Click CLI, yt-dlp for download, pydub for audio trimming, ffmpeg (subprocess) for video trimming.
- `Dockerfile.base` — base image: Python 3.12-slim + ffmpeg. Build once, reuse.
- `Dockerfile` — app layer: copies code, pip installs, sets entrypoint. Fast rebuilds.
- `pyproject.toml` — hatchling build, entry point `clip:main`.
- `docker-compose.yml` — minimal service definition (build + volume mount).

System dependency: **ffmpeg** (only available inside Docker).

## Gotchas

- The cache defaults to `.pyclip-cache/` in the current directory; Docker sets `PYCLIP_CACHE_DIR` to `/output/.pyclip-cache/`. Update the CLI, Dockerfile, and README together if changing cache behavior.
- Video clips (.mp4) use ffmpeg subprocess; audio clips use pydub. Two different code paths.
- `yt-dlp` is imported lazily inside functions (not at module top).
- All progress output goes to stderr (`Console(stderr=True)`).
