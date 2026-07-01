import json
import os
import subprocess
import sys
from pathlib import Path

from pipeline.ffmpeg_bin import ffmpeg_exe


def _env():
    return {**os.environ, "PYTHONUTF8": "1"}


def fetch(url: str, workdir, caption_langs=("ko",)) -> dict:
    """오디오(핵심)와 자막(레이트리밋 민감)을 분리해서 받는다.

    - 1단계: 오디오→mp3 + info.json. 실패하면 예외(치명적).
    - 2단계: 자막(기본 ko만). 429 등으로 실패해도 예외 없이 넘어간다(나중에 fetch_captions 재시도 가능).
      transcript 단계에서 vtt 없으면 그때 명확히 안내.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()

    subprocess.run([
        sys.executable, "-m", "yt_dlp",
        "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--ffmpeg-location", ff,
        "--write-info-json", "--retries", "10", "--extractor-retries", "3",
        "-o", str(workdir / "audio.%(ext)s"),
        url,
    ], check=True, env=_env())

    info = json.loads((workdir / "audio.info.json").read_text(encoding="utf-8"))
    (workdir / "info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    # 원본 오디오는 retrim 소스로 보존: audio.mp3 -> audio.source.mp3
    src = workdir / "audio.mp3"
    if src.exists():
        src.replace(workdir / "audio.source.mp3")

    fetch_captions(url, workdir, caption_langs)

    return {
        "video_id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel"),
        "duration_seconds": info.get("duration"),
        "description": info.get("description"),
        "workdir": str(workdir),
    }


def fetch_captions(url: str, workdir, langs=("ko",)) -> bool:
    """자막만 별도로 받는다. 레이트리밋(429) 등으로 실패해도 False 반환(비치명적)."""
    workdir = Path(workdir)
    try:
        subprocess.run([
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs", "--sub-langs", ",".join(langs), "--sub-format", "vtt",
            "--retries", "10", "--sleep-requests", "2",
            "-o", str(workdir / "audio.%(ext)s"),
            url,
        ], check=True, env=_env())
        return True
    except subprocess.CalledProcessError:
        return False
