from pipeline.timeutil import fmt_time


def apply_cut(analysis: dict, cut: dict) -> dict:
    """analysis.deck(원본 좌표) + cut → study.deck(트림 좌표).

    타임스탬프는 header/line 어느 행에 있어도 된다(AI가 레이아웃 결정):
    - header에 t_seconds → 그 패턴(그룹) 전체의 트림 기준. 범위 밖이면 그룹 통째 제거.
    - line에 t_seconds → 그 줄 개별 트림 기준.
    - t_seconds 없는 line → 소속 그룹(직전 header)의 생존 여부를 따른다.
    범위 안이면 t_seconds를 오프셋하고 표시용 t를 붙인다. label/구조는 AI가 정한 대로 보존.
    line이 하나도 안 붙는 header(고아)는 제거.
    """
    intro = float(cut["intro_end"])
    outro = float(cut["outro_start"])
    if not (0 <= intro < outro):
        raise ValueError(f"cut must satisfy 0 <= intro_end < outro_start (got {intro}, {outro})")

    def _offset(row, ts):
        new = {"kind": row["kind"], "label": row.get("label"),
               "primary": row.get("primary"), "secondary": row.get("secondary")}
        if ts is not None:
            t_rel = round(ts - intro, 3)
            new["t_seconds"] = t_rel
            new["t"] = fmt_time(t_rel)
        return new

    out = []
    pending_header = None
    group_dropped = False
    for row in analysis["deck"]["rows"]:
        if row.get("kind") == "header":
            ts = row.get("t_seconds")
            if ts is not None and not (intro <= ts < outro):
                group_dropped = True
                pending_header = None
                continue
            group_dropped = False
            pending_header = _offset(row, ts)
        else:  # line
            if group_dropped:
                continue
            ts = row.get("t_seconds")
            if ts is not None and not (intro <= ts < outro):
                continue
            if pending_header is not None:
                out.append(pending_header)
                pending_header = None
            out.append(_offset(row, ts))

    return {
        "schema_version": analysis.get("schema_version", "2.0"),
        "type": analysis["type"],
        "source": analysis["source"],
        "audio": {
            "original": "audio.mp3",
            "trimmed": "audio.trimmed.mp3",
            "cut": {"intro_end": intro, "outro_start": outro,
                    "decided_by": cut.get("decided_by", "ai")},
        },
        "deck": {
            "subtitle": analysis["deck"].get("subtitle"),
            "rows": out,
        },
    }


def resolve_cut(current_cut: dict, duration: float, *, coords: str,
                intro=None, outro=None, front=None, back=None) -> dict:
    intro_end = float(current_cut["intro_end"])
    outro_start = float(current_cut["outro_start"])
    if coords == "original":
        if intro is not None:
            intro_end = float(intro)
        if outro is not None:
            outro_start = float(outro)
    elif coords == "edited":
        if front is not None:
            intro_end = intro_end + float(front)
        if back is not None:
            outro_start = outro_start - float(back)
    else:
        raise ValueError("coords must be 'original' or 'edited'")
    if not (0 <= intro_end < outro_start <= duration):
        raise ValueError(f"invalid cut: {intro_end}..{outro_start} (duration {duration})")
    new = dict(current_cut)
    new["history"] = list(current_cut.get("history", [])) + [
        {"intro_end": float(current_cut["intro_end"]), "outro_start": float(current_cut["outro_start"])}
    ]
    new["intro_end"] = round(intro_end, 3)
    new["outro_start"] = round(outro_start, 3)
    new["decided_by"] = "manual"
    return new
