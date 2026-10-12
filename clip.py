#!/usr/bin/env python3
"""Extract audio/video clips from YouTube videos by timestamps."""

import os
import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import click
from pydub import AudioSegment
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    DownloadColumn, TransferSpeedColumn,
)

SUPPORTED_FORMATS = {'.mp3', '.wav', '.mp4'}
TIMESTAMP_RE = re.compile(
    r'^(\d{1,2}(?::\d{2}){0,2})?-(\d{1,2}(?::\d{2}){0,2})?$'
)


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        return parse_qs(parsed.query).get('v', [None])[0]
    if 'youtu.be' in parsed.netloc:
        return parsed.path.lstrip('/')
    return None


def parse_timestamp(ts: str) -> float:
    parts = ts.split(':')
    parts = [float(p) for p in parts]
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Invalid timestamp: {ts}")


def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return (parsed.scheme in ('http', 'https')
            and ('youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc))


def download_audio(url: str, temp_dir: str, cache_dir: str | None, progress: Progress) -> Path:
    import yt_dlp

    if cache_dir:
        video_id = extract_video_id(url)
        if video_id:
            cached = Path(cache_dir) / video_id / 'audio.wav'
            if cached.exists():
                progress.console.print(f"[cyan]Using cached audio for {video_id}[/cyan]")
                return cached

    download_task = progress.add_task("Downloading audio", total=None)

    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                progress.update(download_task, total=total, completed=d.get('downloaded_bytes', 0))
            else:
                progress.update(download_task, total=None, description=f"Downloading audio {d.get('_percent_str', '').strip()}")
        elif d['status'] == 'finished':
            progress.update(download_task, description="Converting")

    dl_dir = cache_dir if cache_dir else temp_dir
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(dl_dir, 'full_audio.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    progress.update(download_task, description="Download complete", completed=True)

    for f in os.listdir(dl_dir):
        if f.endswith('.wav'):
            result = Path(dl_dir) / f
            if cache_dir and extract_video_id(url):
                target = Path(cache_dir) / extract_video_id(url) / 'audio.wav'
                target.parent.mkdir(parents=True, exist_ok=True)
                if result != target:
                    shutil.move(str(result), str(target))
                return target
            return result

    raise RuntimeError("Download failed — no audio file produced")


def download_video(url: str, temp_dir: str, cache_dir: str | None, progress: Progress) -> Path:
    import yt_dlp

    if cache_dir:
        video_id = extract_video_id(url)
        if video_id:
            cached_dir = Path(cache_dir) / video_id
            if cached_dir.exists():
                for f in cached_dir.iterdir():
                    if f.suffix in ('.mp4', '.mkv', '.webm'):
                        progress.console.print(f"[cyan]Using cached video for {video_id}[/cyan]")
                        return f

    download_task = progress.add_task("Downloading video", total=None)

    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                progress.update(download_task, total=total, completed=d.get('downloaded_bytes', 0))
            else:
                progress.update(download_task, total=None, description=f"Downloading video {d.get('_percent_str', '').strip()}")
        elif d['status'] == 'finished':
            progress.update(download_task, description="Processing")

    dl_dir = cache_dir if cache_dir else temp_dir
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(dl_dir, 'full_video.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    progress.update(download_task, description="Download complete", completed=True)

    for f in os.listdir(dl_dir):
        if f.endswith(('.mp4', '.mkv', '.webm')):
            result = Path(dl_dir) / f
            if cache_dir and extract_video_id(url):
                target = Path(cache_dir) / extract_video_id(url) / f
                target.parent.mkdir(parents=True, exist_ok=True)
                if result != target:
                    shutil.move(str(result), str(target))
                return target
            return result

    raise RuntimeError("Download failed — no video file produced")


def extract_clip(audio: AudioSegment, start_s: float, end_s: float) -> AudioSegment:
    start_ms = int(start_s * 1000)
    end_ms = int(end_s * 1000)
    if start_ms >= end_ms:
        raise ValueError(f"Start ({start_s}s) must be before end ({end_s}s)")
    return audio[start_ms:end_ms]


def extract_video_clip(input_path: str, output_path: str, start_s: float, end_s: float) -> None:
    duration = end_s - start_s
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_s),
        '-i', input_path,
        '-t', str(duration),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


@click.command(context_settings={'ignore_unknown_options': True})
@click.argument('url')
@click.argument('clips', nargs=-1, required=True)
@click.option('--keep-raw', is_flag=True, help='Keep the full downloaded file')
@click.option('--no-cache', is_flag=True, help='Skip cache, force fresh download')
@click.option('--temp-dir', type=click.Path(), default=None, help='Override temp directory')
def main(url: str, clips: tuple, keep_raw: bool, no_cache: bool, temp_dir: str | None):
    """Extract audio/video clips from a YouTube video.

    Usage: pyclip URL START-END OUTPUT [START-END OUTPUT ...]

    START-END format: HH:MM:SS-HH:MM:SS; omit START to begin at 0,
    or omit END to continue to the end of the video.

    Supported formats: .mp3, .wav, .mp4
    """
    if not validate_url(url):
        click.echo(f"Error: Invalid YouTube URL: {url}", err=True)
        raise SystemExit(1)

    if len(clips) % 2 != 0:
        click.echo("Error: Each clip needs a timestamp AND an output filename.", err=True)
        click.echo("Usage: pyclip URL 01:30-02:15 out.mp3", err=True)
        raise SystemExit(1)

    clip_specs = []
    for i in range(0, len(clips), 2):
        ts_str, output = clips[i], clips[i + 1]
        match = TIMESTAMP_RE.match(ts_str)
        if not match or not any(match.groups()):
            click.echo(
                f"Error: Invalid timestamp format '{ts_str}'. "
                "Use START-END, e.g. 01:00-01:30, -05:00, or 01:00-",
                err=True,
            )
            raise SystemExit(1)

        ext = Path(output).suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            click.echo(f"Error: Unsupported format '{ext}'. Use .mp3, .wav, or .mp4", err=True)
            raise SystemExit(1)

        start = parse_timestamp(match.group(1)) if match.group(1) else 0.0
        end = parse_timestamp(match.group(2)) if match.group(2) else None
        clip_specs.append((start, end, output))

    clip_specs.sort(key=lambda x: x[0])
    for i in range(1, len(clip_specs)):
        prev_end = clip_specs[i - 1][1]
        curr_start = clip_specs[i][0]
        if prev_end is None or curr_start < prev_end:
            prev_end_description = (
                f"ends at {prev_end}s"
                if prev_end is not None
                else "continues to the end of the video"
            )
            click.echo(
                f"Warning: Clips {i} and {i + 1} overlap "
                f"({clip_specs[i - 1][2]} {prev_end_description}, "
                f"{clip_specs[i][2]} starts at {curr_start}s)",
                err=True,
            )

    has_video = any(Path(s[2]).suffix.lower() == '.mp4' for s in clip_specs)
    has_audio = any(Path(s[2]).suffix.lower() in ('.mp3', '.wav') for s in clip_specs)

    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="pyclip_")
    else:
        os.makedirs(temp_dir, exist_ok=True)

    cache_dir = None if no_cache else '/output/.pyclip-cache'
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    try:
        console = Console(stderr=True)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
        ) as progress:
            video_path = None
            audio_data = None
            duration_s = 0.0

            if has_video:
                video_path = download_video(url, temp_dir, cache_dir, progress)
                probe = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)],
                    capture_output=True, text=True, check=True,
                )
                duration_s = float(probe.stdout.strip())

            if has_audio:
                audio_wav = download_audio(url, temp_dir, cache_dir, progress)
                audio_data = AudioSegment.from_wav(str(audio_wav))
                duration_s = max(duration_s, len(audio_data) / 1000.0)

            clip_task = progress.add_task("Extracting clips", total=len(clip_specs))
            for idx, (start, end, output) in enumerate(clip_specs, 1):
                if end is None:
                    end = duration_s
                elif end > duration_s:
                    progress.console.print(
                        f"[yellow]Warning: Clip {idx} ({output}) ends at {end}s "
                        f"but source is only {duration_s:.1f}s. Clipping to end.[/yellow]"
                    )
                    end = duration_s

                if start >= end:
                    raise ValueError(
                        f"Clip {idx} ({output}) starts at {start}s, "
                        f"which is not before its end at {end}s"
                    )

                ext = Path(output).suffix.lower()
                if ext == '.mp4':
                    extract_video_clip(str(video_path), output, start, end)
                else:
                    clip_audio = extract_clip(audio_data, start, end)
                    clip_audio.export(output, format=ext.lstrip('.'))
                progress.advance(clip_task)

            progress.console.print(f"[green]Done![/green] {len(clip_specs)} clip(s) extracted.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        if not keep_raw and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
