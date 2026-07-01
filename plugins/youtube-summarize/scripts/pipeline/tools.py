import json
import os
import shutil
import subprocess
import sys

from pipeline.paths import workdir_for, work_dir, new_history_slot
from pipeline.fetch import fetch
from pipeline.transcribe import transcript_from_vtt
from pipeline.derive import apply_cut, resolve_cut
from pipeline.trim import trim
from pipeline.build_ppt import build_ppt
from pipeline.autoplay import build_autoplay
from pipeline.schema import validate_analysis, validate_study
from pipeline.logging_setup import setup_logging

log = setup_logging()


def _video_meta(url: str):
    """다운로드 없이 video_id와 제목을 조회. (제목 폴더명용, UTF-8 디코딩)"""
    out = subprocess.run([sys.executable, "-m", "yt_dlp", "--skip-download",
                          "--print", "%(id)s", "--print", "%(title)s", url],
                         capture_output=True, text=True, encoding="utf-8", check=True,
                         env={**os.environ, "PYTHONUTF8": "1"})
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    return lines[0], (lines[1] if len(lines) > 1 else "")


def collect(url: str) -> dict:
    """오디오·자막 다운로드 + 대본 생성. 중간물은 <workdir>/.work 에 둔다.

    반환한 work_dir 의 transcript.json/info.json 을 Claude가 읽어 분석하고,
    analysis.json 을 work_dir(=.work) 에 쓴다.
    """
    vid, title = _video_meta(url)
    wd = workdir_for(vid, title=title)
    work = work_dir(wd)
    meta = fetch(url, work)
    vtt = work / "audio.ko.vtt"
    if not vtt.exists():
        raise RuntimeError("자막(ko)을 받지 못했습니다(일시적 제한일 수 있어요). 잠시 후 다시 시도해 주세요.")
    tr = transcript_from_vtt(vtt, work / "transcript.json")
    log.info("collected %s (%d cues) -> %s", vid, len(tr["cues"]), wd)
    return {"video_id": vid, "workdir": str(wd), "work_dir": str(work),
            "analysis_path": str(work / "analysis.json"),
            "title": meta["title"], "channel": meta["channel"],
            "duration_seconds": meta["duration_seconds"]}


def render(video_id: str) -> dict:
    """Claude가 .work/analysis.json(type/cut/deck)을 읽어 study.json·트림 MP3·PPT 생성.

    중간물(analysis/cut/study)은 .work 에, 최종물(slides.pptx·audio.trimmed.mp3)은 workdir 루트에.
    source(title/channel/duration)는 info.json에서 서버가 채운다.
    """
    wd = workdir_for(video_id)
    work = work_dir(wd)
    doc = json.loads((work / "analysis.json").read_text(encoding="utf-8"))
    info = json.loads((work / "info.json").read_text(encoding="utf-8"))
    analysis = {
        "schema_version": "2.0",
        "type": doc["type"],
        "source": {"url": info.get("webpage_url"), "video_id": info.get("id"),
                   "title": info.get("title"), "channel": info.get("channel"),
                   "duration_seconds": info.get("duration")},
        "classification": doc.get("classification", {"type": doc["type"]}),
        "cut": doc["cut"],
        "deck": {"subtitle": doc["deck"].get("subtitle"), "rows": doc["deck"]["rows"]},
    }
    errs = validate_analysis(analysis)
    if errs:
        raise ValueError(f"analysis 검증 실패: {errs}")
    # 서버가 채운 source까지 반영해 다시 저장(정본)
    (work / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    cut = analysis["cut"]
    (work / "cut.json").write_text(json.dumps({**cut, "history": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    study = apply_cut(analysis, cut)
    serrs = validate_study(study)
    if serrs:
        raise ValueError(f"study 검증 실패: {serrs}")
    (work / "study.json").write_text(json.dumps(study, ensure_ascii=False, indent=2), encoding="utf-8")
    trim(work / "audio.source.mp3", cut["intro_end"], cut["outro_start"], wd / "audio.trimmed.mp3")
    build_ppt(study, wd / "slides.pptx")
    n = sum(1 for r in study["deck"]["rows"] if r["kind"] == "line")
    log.info("rendered %s (%d sentences)", video_id, n)
    return {"pptx_path": str(wd / "slides.pptx"), "mp3_path": str(wd / "audio.trimmed.mp3"),
            "study_json_path": str(work / "study.json"), "n_sentences": n}


def embed_audio(video_id: str, leadin: float = 1.0) -> dict:
    """render 산출물(slides.pptx + audio.trimmed.mp3)로 음성 포함 자동재생 덱을 만든다.

    각 슬라이드에 그 구간 오디오 임베드(열리면 자동재생) + 구간 길이만큼 뒤 자동 전환.
    아무 페이지로 점프해도 그 페이지 구간이 처음부터 재생된다. 원본 slides.pptx 는 그대로 둔다.
    """
    wd = workdir_for(video_id)
    work = work_dir(wd)
    study = json.loads((work / "study.json").read_text(encoding="utf-8"))
    res = build_autoplay(study, wd, leadin=leadin)
    log.info("embedded audio %s -> %s (%d slides)", video_id,
             res["autoplay_pptx_path"], res["n_content_slides"])
    return res


def retrim(video_id: str, coords: str, intro=None, outro=None, front=None, back=None) -> dict:
    """트림만 재조정. 원본(.work/audio.source.mp3)에서 다시 자른다(무손실).

    덮어쓰기 전에 기존 최종물(slides.pptx·audio.trimmed.mp3)을 .history/<stamp>/ 로 백업한다.
    """
    wd = workdir_for(video_id)
    work = work_dir(wd)
    analysis = json.loads((work / "analysis.json").read_text(encoding="utf-8"))
    cur = json.loads((work / "cut.json").read_text(encoding="utf-8"))
    dur = analysis["source"]["duration_seconds"]
    new_cut = resolve_cut(cur, dur, coords=coords, intro=intro, outro=outro, front=front, back=back)

    # 덮어쓰기 전 백업 (있는 것만)
    slot = new_history_slot(wd)
    backed = []
    for name in ("slides.pptx", "audio.trimmed.mp3"):
        p = wd / name
        if p.exists():
            shutil.copy2(p, slot / name)
            backed.append(name)

    (work / "cut.json").write_text(json.dumps(new_cut, ensure_ascii=False, indent=2), encoding="utf-8")
    study = apply_cut(analysis, new_cut)
    (work / "study.json").write_text(json.dumps(study, ensure_ascii=False, indent=2), encoding="utf-8")
    trim(work / "audio.source.mp3", new_cut["intro_end"], new_cut["outro_start"], wd / "audio.trimmed.mp3")
    build_ppt(study, wd / "slides.pptx")
    return {"pptx_path": str(wd / "slides.pptx"), "mp3_path": str(wd / "audio.trimmed.mp3"),
            "backup_dir": str(slot), "backed_up": backed,
            "cut": {"intro_end": new_cut["intro_end"], "outro_start": new_cut["outro_start"]}}
