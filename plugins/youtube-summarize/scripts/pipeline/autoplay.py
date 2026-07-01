"""slides.pptx + audio.trimmed.mp3 → slides.autoplay.pptx (음성 포함 자동재생 덱).

각 내용 슬라이드에 그 슬라이드 구간의 오디오를 임베드하고 '슬라이드가 열리면 자동재생'
+ 구간 길이만큼 뒤 자동 전환(advTm)을 건다. 오디오를 슬라이드별로 나눠 넣으므로,
자동 진행이든 사용자가 아무 페이지로 점프하든 그 페이지 구간이 처음부터 재생된다.

레이아웃/페이지네이션은 build_ppt 와 동일 함수를 재사용해 슬라이드↔구간 매핑을 일치시킨다.
python-pptx 는 미디어 임베드·전환 API가 없어 OOXML 을 직접 주입한다.

주의(검증됨): 미디어 개체를 화면 밖(음수 좌표)에 두면 PowerPoint 가 자동재생을 안 걸고
스피커 아이콘도 안 보인다 → 반드시 슬라이드 안(우상단 작은 아이콘)에 배치한다.
"""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches

from pipeline.build_ppt import _groups, _paginate, BOTTOM, TOP
from pipeline.ffmpeg_bin import ffmpeg_exe

TITLE_HOLD = 3.0  # 제목 슬라이드 표시 시간(초, 무음)
VIDEO_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video"
AUDIO_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio"
SLD_ORDER = ["p:cSld", "p:clrMapOvr", "p:transition", "p:timing", "p:extLst"]


def _audio_duration(mp3: Path) -> float:
    """ffmpeg -i 로 오디오 총 길이(초) 측정."""
    out = subprocess.run([ffmpeg_exe(), "-i", str(mp3)], capture_output=True)
    err = out.stderr.decode("utf-8", "replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
    if not m:
        raise RuntimeError("오디오 길이를 읽지 못했습니다.")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _slide_starts(study: dict):
    """build_ppt 와 동일한 페이지네이션으로 내용 슬라이드별 시작 시각(트림 기준)을 구한다."""
    prs = Presentation()
    usable_h = prs.slide_height - TOP - BOTTOM
    pages = _paginate(_groups(study["deck"]["rows"]), usable_h)
    return [pg[0][0]["t_seconds"] for pg in pages]


def _split_segments(mp3: Path, starts, total: float, seg_dir: Path, leadin: float):
    """트림 오디오를 슬라이드 경계에서 구간별로 분할. leadin>0 이면 시작을 그만큼 앞당김(끝은 그대로)."""
    seg_dir.mkdir(parents=True, exist_ok=True)
    ends = starts[1:] + [total]
    ff = ffmpeg_exe()
    segs = []
    for i, (s, e) in enumerate(zip(starts, ends), start=1):
        cs = max(0.0, round(s - leadin, 3))
        dur = round(e - cs, 3)
        out = seg_dir / f"seg{i:02d}.mp3"
        subprocess.run([ff, "-y", "-ss", f"{cs}", "-i", str(mp3), "-t", f"{dur}",
                        "-c:a", "libmp3lame", "-q:a", "4", str(out)],
                       check=True, capture_output=True)
        segs.append({"file": str(out), "dur": dur})
    return segs


def _insert_ordered(sld, elem):
    """<p:sld> 자식 스키마 순서를 지켜 삽입."""
    want = "p:" + elem.tag.split("}")[-1]
    want_idx = SLD_ORDER.index(want)
    ref = None
    for child in sld:
        c_name = "p:" + child.tag.split("}")[-1]
        if c_name in SLD_ORDER and SLD_ORDER.index(c_name) > want_idx:
            ref = child
            break
    (sld.append(elem) if ref is None else ref.addprevious(elem))


def _add_transition(slide, adv_ms: int):
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    xml = f'<p:transition {nsdecls("p")} spd="med" advClick="1" advTm="{adv_ms}"><p:fade/></p:transition>'
    _insert_ordered(sld, parse_xml(xml))


def _add_autoplay_audio(slide, mp3_path: str, dur_ms: int, sw) -> int:
    """우상단에 보이는 작은 스피커 아이콘으로 오디오 임베드 + 슬라이드 열리면 자동재생."""
    movie = slide.shapes.add_movie(
        mp3_path, sw - Inches(0.6), Inches(0.12), Inches(0.45), Inches(0.45),
        poster_frame_image=None, mime_type="audio/mpeg",
    )
    spid = movie.shape_id
    pic = movie._element
    nvpr = pic.find(qn("p:nvPicPr")).find(qn("p:nvPr"))
    vf = nvpr.find(qn("a:videoFile"))
    if vf is not None:  # add_movie 는 videoFile 로 만든다 → 오디오로 교정
        vf.tag = qn("a:audioFile")
    timing_xml = (
        f'<p:timing {nsdecls("p", "a", "r")}><p:tnLst><p:par>'
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
        '<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        '<p:par><p:cTn id="5" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="afterEffect">'
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        f'<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="6" dur="{dur_ms}" fill="hold"/>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd>'
        '</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        '</p:seq>'
        '<p:audio><p:cMediaNode vol="80000"><p:cTn id="7" fill="hold" display="0">'
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode></p:audio>'
        '</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'
    )
    sld = slide._element
    for old in sld.findall(qn("p:timing")):
        sld.remove(old)
    _insert_ordered(sld, parse_xml(timing_xml))
    return spid


def _fix_audio_rel_types(pptx_path: Path) -> int:
    """add_movie 가 남긴 mp3 의 관계타입 video → audio 로 교정(audioFile 과 일치)."""
    pat = re.compile(r'Type="' + re.escape(VIDEO_RT) + r'"(\s+Target="\.\./media/[^"]+\.mp3")')
    zin = zipfile.ZipFile(pptx_path, "r")
    items = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    zin.close()
    fixed = 0
    for name in list(items):
        if re.match(r"ppt/slides/_rels/slide\d+\.xml\.rels$", name):
            s2, n = pat.subn(f'Type="{AUDIO_RT}"\\1', items[name].decode("utf-8"))
            if n:
                items[name] = s2.encode("utf-8")
                fixed += n
    tmp = str(pptx_path) + ".relfix"
    zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for n, data in items.items():
        zout.writestr(infos[n], data)
    zout.close()
    os.replace(tmp, pptx_path)
    return fixed


def build_autoplay(study: dict, wd, leadin: float = 1.0) -> dict:
    """slides.pptx + audio.trimmed.mp3 → slides.autoplay.pptx.

    leadin: 각 구간을 시작점보다 몇 초 앞당겨 자를지(중복 허용, 첫 구간은 0에서 클램프). 끝은 그대로.
    대상 파일이 PowerPoint 에서 열려 잠겨 있으면 slides.autoplay.new.pptx 로 대체 저장한다.
    """
    wd = Path(wd)
    src = wd / "slides.pptx"
    mp3 = wd / "audio.trimmed.mp3"
    out = wd / "slides.autoplay.pptx"
    if not src.exists() or not mp3.exists():
        raise FileNotFoundError("먼저 render 로 slides.pptx 와 audio.trimmed.mp3 를 만들어야 합니다.")

    total = _audio_duration(mp3)
    starts = _slide_starts(study)
    segs = _split_segments(mp3, starts, total, wd / ".work" / "seg", leadin)

    prs = Presentation(str(src))
    sw = prs.slide_width
    slides = list(prs.slides)
    if len(slides) != 1 + len(segs):
        raise RuntimeError(f"슬라이드 수({len(slides)})와 구간 수(1+{len(segs)})가 맞지 않습니다.")

    _add_transition(slides[0], int(TITLE_HOLD * 1000))  # 제목: 무음 후 전환
    for seg, slide in zip(segs, slides[1:]):             # 내용 슬라이드
        dur_ms = int(seg["dur"] * 1000)
        _add_autoplay_audio(slide, seg["file"], dur_ms, sw)
        _add_transition(slide, dur_ms)

    build = str(out) + ".building"
    prs.save(build)
    _fix_audio_rel_types(Path(build))
    Presentation(build)  # 손상 여부 확인(깨졌으면 예외)

    locked = False
    try:
        os.replace(build, out)
    except PermissionError:  # 대상이 PowerPoint 에서 열려 잠김
        out = wd / "slides.autoplay.new.pptx"
        os.replace(build, out)
        locked = True

    return {"autoplay_pptx_path": str(out), "n_content_slides": len(segs),
            "leadin_seconds": leadin, "audio_seconds": round(total, 2), "locked_fallback": locked}
