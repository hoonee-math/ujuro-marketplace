def fmt_time(seconds) -> str:
    if seconds is None or seconds < 0:
        raise ValueError("seconds must be >= 0")
    total = int(seconds)  # 내림(floor): seek 라벨이 문장 시작을 넘어가지 않도록
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def parse_time(text) -> float:
    text = str(text).strip()
    if ":" not in text:
        return float(text)
    parts = [float(p) for p in text.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"bad time: {text}")
