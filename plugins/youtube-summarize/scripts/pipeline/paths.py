import os
import re
from datetime import datetime
from pathlib import Path


def output_root() -> Path:
    """산출물 루트. 기본은 현재 작업 폴더(cwd) 밑 'youtube-summarize'.

    스킬은 사용자의 작업 폴더에서 실행되므로 Path.cwd() 기준이 된다.
    (~/Downloads 같은 사용자가 모르는 곳에 저장하지 않는다.)
    테스트/특수 상황을 위해 YOUTUBE_SUMMARIZE_OUTPUT_DIR 로 덮어쓸 수 있다.
    """
    env = os.environ.get("YOUTUBE_SUMMARIZE_OUTPUT_DIR")
    root = Path(env) if env else (Path.cwd() / "youtube-summarize")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_name(title: str, maxlen: int = 80) -> str:
    """파일시스템 안전한 폴더명으로. Windows 금지문자·제어문자 제거."""
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", title or "")
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    if len(s) > maxlen:
        s = s[:maxlen].rstrip()
    return s or "video"


def _find_workdir(root: Path, video_id: str):
    """기존 작업 폴더를 video_id로 찾는다(정확히 id이거나 '... [id]' 로 끝나는 폴더)."""
    for p in root.iterdir():
        if p.is_dir() and (p.name == video_id or p.name.endswith(f"[{video_id}]")):
            return p
    return None


def workdir_for(video_id: str, title=None) -> Path:
    """영상 작업 폴더 '<제목>-[video_id]'. 이미 있으면 그대로, 없으면 생성.

    최종물(slides.pptx, audio.trimmed.mp3)은 이 폴더 루트에 둔다.
    render/retrim은 title 없이 호출해도 video_id로 기존 폴더를 찾는다.
    """
    root = output_root()
    existing = _find_workdir(root, video_id)
    if existing:
        return existing
    name = f"{_safe_name(title)}-[{video_id}]" if title else video_id
    wd = root / name
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def work_dir(workdir) -> Path:
    """중간물 폴더 <workdir>/.work (원본 오디오·자막·transcript·analysis·cut·study)."""
    d = Path(workdir) / ".work"
    d.mkdir(parents=True, exist_ok=True)
    return d


def history_dir(workdir) -> Path:
    """버전 백업 루트 <workdir>/.history."""
    d = Path(workdir) / ".history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_history_slot(workdir) -> Path:
    """덮어쓰기 직전 백업용 타임스탬프 폴더 <workdir>/.history/<stamp>."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    d = history_dir(workdir) / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def logs_dir() -> Path:
    d = output_root() / ".logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
