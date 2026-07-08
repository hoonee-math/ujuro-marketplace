"""slides.pptx + audio.trimmed.mp3 → slides.mp4 (페이지 자동전환 학습 영상).

각 페이지를 PNG 로 렌더하고 그 구간 오디오 길이만큼 정지 클립으로 만든 뒤 concat 한다.
페이지네이션은 build_ppt_compact.content_pages(= autoplay._slide_starts)와 동일하므로
프레임 N과 세그먼트 N이 정확히 맞는다.

슬라이드→PNG 는 PowerPoint COM(render_slides.ps1) 이라 Windows + MS PowerPoint 가 필요하다.
"""
import subprocess
from pathlib import Path

from pipeline.autoplay import _audio_duration, _slide_starts, _split_segments
from pipeline.ffmpeg_bin import ffmpeg_exe

SCRIPTS_DIR = Path(__file__).resolve().parent.parent   # .../scripts
RENDER_PS1 = SCRIPTS_DIR / "render_slides.ps1"
FRAME_W, FRAME_H = 1754, 1240
SCALE_EVEN = "scale=trunc(iw/2)*2:trunc(ih/2)*2"


def _render_frames(pptx: Path, out_dir: Path) -> list:
    """render_slides.ps1 로 슬라이드별 PNG 생성 → slide-1.png..slide-K.png 정렬 리스트."""
    try:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(RENDER_PS1),
                        "-Src", str(pptx), "-OutDir", str(out_dir),
                        "-Width", str(FRAME_W), "-Height", str(FRAME_H)],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "render-video 프레임 렌더 실패 — Windows + MS PowerPoint 가 필요합니다.\n" + (e.stderr or "")
        ) from e
    frames = sorted(out_dir.glob("slide-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    if not frames:
        raise RuntimeError("프레임(PNG)이 생성되지 않았습니다.")
    return frames


# 정지 슬라이드라 낮은 fps + ultrafast 로 충분(인코딩 빠르고 파일 작음). 정합/호환은 전 클립 공통값으로.
FPS = "10"


def _content_clip(ff: str, png: Path, seg_mp3: str, dur: float, out: Path) -> None:
    """정지 이미지 + 구간 오디오를 정확히 dur 초 클립으로. (-t 로 하드 캡 — -loop 이미지 스트림이
    -shortest 로는 GOP 경계까지 넘쳐 오디오 종료 시점에 안 맞으므로, 아는 길이로 결정론적 컷.)"""
    subprocess.run([ff, "-y", "-loop", "1", "-i", str(png), "-i", str(seg_mp3), "-t", f"{dur}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                    "-r", FPS, "-vf", SCALE_EVEN,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def _title_clip(ff: str, png: Path, hold: float, out: Path) -> None:
    """타이틀: 무음 트랙 + 정확히 hold 초(-t 로 하드 캡)."""
    subprocess.run([ff, "-y", "-loop", "1", "-i", str(png),
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{hold}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                    "-r", FPS, "-vf", SCALE_EVEN,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def build_video(study: dict, wd, leadin: float = 0.0, title_hold: float = 3.0,
                include_title: bool = False) -> dict:
    wd = Path(wd)
    src = wd / "slides.pptx"
    mp3 = wd / "audio.trimmed.mp3"
    out = wd / "slides.mp4"
    if not src.exists() or not mp3.exists():
        raise FileNotFoundError("먼저 render 로 slides.pptx 와 audio.trimmed.mp3 를 만들어야 합니다.")

    work = wd / ".work"
    total = _audio_duration(mp3)
    starts = _slide_starts(study)
    segs = _split_segments(mp3, starts, total, work / "seg", leadin)
    frames = _render_frames(src, work / "frames")
    if len(frames) != 1 + len(segs):
        raise RuntimeError(f"프레임 수({len(frames)}) != 1(타이틀)+세그먼트({len(segs)}). 매핑 불일치.")

    ff = ffmpeg_exe()
    clips_dir = work / "clips"
    if clips_dir.exists():
        for old in clips_dir.glob("clip-*.mp4"):
            old.unlink()
    clips_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    if include_title:
        tclip = clips_dir / "clip-00.mp4"
        _title_clip(ff, frames[0], title_hold, tclip)
        clip_paths.append(tclip)
    for i, seg in enumerate(segs):
        cclip = clips_dir / f"clip-{i + 1:02d}.mp4"
        _content_clip(ff, frames[i + 1], seg["file"], seg["dur"], cclip)
        clip_paths.append(cclip)

    list_file = work / "video_list.txt"
    list_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in clip_paths), encoding="utf-8")
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-c", "copy", str(out)], check=True, capture_output=True)

    secs = sum(s["dur"] for s in segs) + (title_hold if include_title else 0.0)
    return {"video_path": str(out), "n_content_slides": len(segs),
            "include_title": include_title, "title_hold_seconds": title_hold,
            "leadin_seconds": leadin, "video_seconds": round(secs, 2)}
