# pyclip

Extract audio/video clips from YouTube videos by timestamps.

## Why pyclip?

No existing Python package combines YouTube downloading with timestamp-based extraction. pyclip fills that gap:

| Tool | Download YouTube audio/video | Extract clips by timestamps | Single command |
|------|:----------------------------:|:---------------------------:|:--------------:|
| **pyclip** | ✓ | ✓ | ✓ |
| yt-dlp | ✓ | ✗ | ✗ |
| pytube | ✓ | ✗ | ✗ |
| pydub | ✗ | ✓ | ✗ |

**yt-dlp** and **pytube** download full videos/audio but can't trim by timestamp in one step.
**pydub** trims audio files but has no YouTube integration.
**pyclip** does both — download and extract — in a single command. Docker is the recommended,
most hassle-free way to run it: the image includes Python, the app dependencies, and FFmpeg, so
you don't need to install or configure them on your machine.

## Requirements

- Docker (recommended; handles the app and system dependencies for you)
- For local runs only: Python 3.10 or newer and FFmpeg (`ffmpeg` and `ffprobe` on your `PATH`)

## Run locally

Choose this if you prefer not to use Docker. It requires installing and maintaining Python,
the Python dependencies, and FFmpeg yourself. For the simpler setup, use [Run with Docker](#run-with-docker).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Install FFmpeg using your operating system's package manager or installer, and ensure both
`ffmpeg` and `ffprobe` are available on your `PATH`. On Windows PowerShell, use these commands
to create and activate the environment:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
```

Run `pyclip` from the directory where you want the download cache stored:

```bash
pyclip "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  01:00-01:30 clip.mp4
```

Downloaded media is cached in `.pyclip-cache/` in the current directory. Use `--no-cache` to
skip the cache.

## Run with Docker

```bash
docker build -t pyclip .
docker run --rm -v $(pwd):/output pyclip <URL> <START-END> <OUTPUT> [START-END OUTPUT ...]
```

### Timestamp formats

`START-END` uses the timestamp formats below. Either side may be omitted:

| Format | Example |
|--------|---------|
| `SS` | `90` |
| `MM:SS` | `01:30` |
| `HH:MM:SS` | `01:30:00` |

- `01:00-` extracts from 1:00 to the end of the video.
- `-05:00` extracts from the beginning through 5:00 (equivalent to `00:00-05:00`).
- `01:00-01:30` extracts from 1:00 through 1:30.

### Supported output formats

`.mp3`, `.wav`, `.mp4`

## Examples

**Single clip (MP3):**

```bash
docker run --rm -v $(pwd):/output pyclip \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  01:00-01:30 /output/clip.mp3
```

**Video clip (MP4):**

```bash
docker run --rm -v $(pwd):/output pyclip \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  01:00-01:30 /output/clip.mp4
```

**Mixed audio and video clips:**

```bash
docker run --rm -v $(pwd):/output pyclip \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  01:00-01:30 /output/intro.mp3 \
  02:15-03:45 /output/scene.mp4 \
  04:00-04:30 /output/outro.wav
```

**Keep the full downloaded file:**

```bash
docker run --rm -v $(pwd):/output pyclip \
  --keep-raw \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  01:00-01:30 /output/clip.mp4
```

## Options

| Flag | Description |
|------|-------------|
| `--keep-raw` | Keep the full downloaded file after extraction |
| `--no-cache` | Skip cache, force fresh download |
| `--temp-dir PATH` | Override the temporary directory used during download |

## Caching

Downloaded videos/audio are cached in `.pyclip-cache/` inside your output directory. Subsequent requests for the same video reuse the cache automatically.

```bash
# First run — downloads and caches
docker run --rm -v $(pwd):/output pyclip \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 01:00-01:30 /output/clip1.mp3

# Second run — reuses cache (no download)
docker run --rm -v $(pwd):/output pyclip \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 01:30-02:00 /output/clip2.mp3

# Force fresh download
docker run --rm -v $(pwd):/output pyclip \
  --no-cache "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 01:00-01:30 /output/clip3.mp3
```
