def _check_source(src, errs):
    for k in ("url", "video_id", "title", "channel", "duration_seconds"):
        if k not in src:
            errs.append(f"source.{k} missing")


def _check_rows(rows, errs, *, require_t):
    """공통 deck.rows 검증. require_t=True면 t_seconds 있는 line은 't' 문자열도 요구(study)."""
    for i, r in enumerate(rows):
        kind = r.get("kind")
        if kind not in ("header", "line"):
            errs.append(f"rows[{i}].kind must be header|line (got {kind!r})")
        if not r.get("primary"):
            errs.append(f"rows[{i}].primary missing")
        if require_t and r.get("t_seconds") is not None and "t" not in r:
            errs.append(f"rows[{i}] has t_seconds but missing 't' (display)")


def validate_study(d: dict) -> list:
    errs = []
    if d.get("type") not in ("english_study", "summary"):
        errs.append("type must be english_study|summary")
    _check_source(d.get("source", {}), errs)
    if d.get("type") == "english_study" and "cut" not in d.get("audio", {}):
        errs.append("audio.cut missing")
    deck = d.get("deck")
    if not isinstance(deck, dict) or "rows" not in deck:
        errs.append("deck.rows missing")
    else:
        _check_rows(deck["rows"], errs, require_t=True)
    return errs


def validate_analysis(d: dict) -> list:
    errs = []
    if d.get("type") not in ("english_study", "summary"):
        errs.append("type must be english_study|summary")
    _check_source(d.get("source", {}), errs)
    if d.get("type") == "english_study" and "cut" not in d:
        errs.append("cut missing")
    deck = d.get("deck")
    if not isinstance(deck, dict) or "rows" not in deck:
        errs.append("deck.rows missing")
    else:
        _check_rows(deck["rows"], errs, require_t=False)
    return errs
