"""자막(VTT) → 정규화 대본. YouTube 자동자막의 롤링(중복 누적)을 de-roll 한다.

Whisper 대신 자막을 1차 소스로 사용한다(캡션이 영어 패턴+한국어 뜻을 타임스탬프째로 담음).
자막이 없는 영상용 STT 폴백은 향후 필요 시 추가.
"""
import json
import re
from pathlib import Path


def _parse_vtt(vtt_text: str):
    cues = []
    for block in re.split(r"\n\n+", vtt_text):
        lines = block.strip().splitlines()
        tl = next((l for l in lines if "-->" in l), None)
        if not tl:
            continue
        start = tl.split("-->")[0].strip()
        m = re.match(r"(?:(\d+):)?(\d+):(\d+)[.,](\d+)", start)
        if not m:
            continue
        secs = (int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60
                + int(m.group(3)) + int(m.group(4)) / 1000)
        body = " ".join(l for l in lines
                        if "-->" not in l and l.strip() != "WEBVTT" and not l.strip().isdigit())
        body = re.sub(r"<[^>]+>", "", body)        # 인라인 타이밍/색상 태그 제거
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            cues.append((round(secs, 3), body))
    return cues


def _deroll(cues):
    """롤링 자막을 겹침 병합으로 복원. 각 세그먼트에 등장 시각을 부여."""
    segments = []
    acc = ""
    for start, text in cues:
        maxk = min(len(acc), len(text))
        ov = 0
        for k in range(maxk, 0, -1):
            if acc.endswith(text[:k]):
                ov = k
                break
        new = text[ov:].strip()
        if new:
            segments.append({"start": start, "text": new})
            acc = (acc + " " + new)[-300:]
    return segments


def transcript_from_vtt(vtt_path, out_json) -> dict:
    cues = _parse_vtt(Path(vtt_path).read_text(encoding="utf-8"))
    segs = _deroll(cues)
    result = {"source": "captions", "cues": segs}
    Path(out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
