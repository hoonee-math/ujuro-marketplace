"""A4 세로 프린트 덱 렌더러 — 영어 예문 연습 인쇄물.

여러 프린트 포맷(mode)이 계속 추가될 수 있는 구조다:
- mode = 추출기(MODES) + 스타일(STYLES). 추출기는 study.json 의 deck.rows 에서
  item(원형 번호 하나로 묶이는 문장들)을 뽑고, 렌더링·페이지네이션은 공유한다.
- 새 포맷 추가 = 추출기·스타일 등록 (+ references/steps/a4-print.md 표에 한 줄).

item 구조: {"pattern": <영어 템플릿|None>, "lines": [(영어, 한글), ...]}
- pattern 이 있고 스타일이 highlight=True 면, 각 예문에서 템플릿 고정어 구간을
  청색 볼드로 강조한다 (시제 변화는 퍼지 매치로 흡수).
페이지네이션: 앞 페이지부터 채우고 나머지는 마지막 페이지에.
item(번호 묶음)은 페이지를 넘어 분할하지 않고, 배지는 묶음 세로 중앙에 하나만 그린다.

지원 mode:
- first: 패턴별 대표(첫) 예문 1문장씩 한 줄로. (예: 54패턴 → 54줄, 27줄×2페이지)
- all:   패턴별 모든 예문을 한 번호로 묶어 출력. 패턴 부분 청색 볼드,
         한 줄 유지(word_wrap 없음, 폰트 11.5/11pt — 긴 문장이 A4 폭에 들어가는 상한).
"""
import re

from pptx import Presentation
from pptx.util import Cm, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

# A4 세로
PAGE_W = Cm(21.0)
PAGE_H = Cm(29.7)

# 공통 레이아웃
MARGIN_X = Cm(1.4)
TOP = Cm(1.3)
BOTTOM = Cm(0.8)
CIRCLE_D = Cm(0.75)
TEXT_GAP = Cm(0.35)       # 배지와 문장 사이
NUM_PT = 11

KOR_FONT = "맑은 고딕"

RED = RGBColor(0xE0, 0x2B, 0x2B)     # 번호 배지
BLUE = RGBColor(0x1E, 0x50, 0xC0)    # 예문 안 '패턴' 강조 (all 모드)
DARK = RGBColor(0x20, 0x20, 0x20)
GRAY = RGBColor(0x66, 0x66, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

DEFAULT_MAX_PER_PAGE = 27

# mode 별 스타일 — row_h(줄 높이), 폰트, 줄바꿈 허용, 묶음 간 간격, 패턴 강조 여부
STYLES = {
    "first": {"row_h": Cm(0.99), "eng_pt": 12.5, "kor_pt": 11, "eng_font": "Segoe UI",
              "wrap": True, "group_gap": Cm(0.0), "highlight": False},
    "all": {"row_h": Cm(0.762), "eng_pt": 11.5, "kor_pt": 11, "eng_font": "Arial",
            "wrap": False, "group_gap": Cm(0.38), "highlight": True},
}


# ---------- mode 별 추출기 ----------

def _extract_first(rows: list) -> list:
    """각 header 다음의 첫 line 만 → item 당 문장 1줄."""
    items, i = [], 0
    while i < len(rows):
        if rows[i]["kind"] == "header":
            j = i + 1
            while j < len(rows) and rows[j]["kind"] != "line":
                j += 1
            if j < len(rows):
                row = rows[j]
                items.append({"pattern": None,
                              "lines": [(row["primary"], row.get("secondary") or "")]})
            i = j
        else:
            i += 1
    return items


def _extract_all(rows: list) -> list:
    """header 당 모든 line 을 한 item 으로. 헤더의 영어 템플릿은 강조용으로 보관."""
    items, cur = [], None
    for row in rows:
        if row["kind"] == "header":
            cur = {"pattern": row["primary"], "lines": []}
            items.append(cur)
        elif row["kind"] == "line" and cur is not None:
            cur["lines"].append((row["primary"], row.get("secondary") or ""))
    return [it for it in items if it["lines"]]


MODES = {
    "first": _extract_first,
    "all": _extract_all,
}


# ---------- 패턴 강조 (all 모드) ----------

def _find_seg(example: str, seg: str):
    """seg(패턴 고정어)를 example 안에서 찾는다.
    1) 단어 경계 정확 매치. 2) 실패 시 단어열 퍼지 매치(앞 3~4글자 공유)로
    시제 변화(turns→turned 등)를 흡수한다."""
    m = re.search(r"(?<![A-Za-z])" + re.escape(seg) + r"(?![A-Za-z])", example)
    if m:
        return (m.start(), m.end())
    seg_words = seg.split()
    toks = [(mm.group(), mm.start(), mm.end()) for mm in re.finditer(r"[A-Za-z']+", example)]
    n = len(seg_words)
    for i in range(len(toks) - n + 1):
        ok = True
        for j in range(n):
            a = seg_words[j].lower().strip("'")
            b = toks[i + j][0].lower().strip("'")
            if a == b:
                continue
            pl = min(4, len(a), len(b))
            if pl >= 3 and a[:pl] == b[:pl]:
                continue
            ok = False
            break
        if ok:
            return (toks[i][1], toks[i + n - 1][2])
    return None


def _pattern_runs(example: str, pattern: str) -> list:
    """'I'm really into ~' 템플릿에서 '~'를 뺀 고정어 구간만 (텍스트, True)로 표시."""
    segs = [s.strip(" ?.!,") for s in pattern.split("~")]
    segs = [s for s in segs if s]
    spans = sorted(sp for seg in segs if (sp := _find_seg(example, seg)))
    runs, i = [], 0
    for a, b in spans:
        if a < i:
            continue
        if a > i:
            runs.append((example[i:a], False))
        runs.append((example[a:b], True))
        i = b
    if i < len(example):
        runs.append((example[i:], False))
    return runs


# ---------- 공유 렌더링 ----------

def _zero_margins(tf):
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)


def _add_run(p, text, size, color, font, bold=False):
    """run 추가 + East-Asian 폰트까지 명시(한글 폰트 대체 방지)."""
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = font
    rPr = r._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", KOR_FONT)
    return r


def _draw_badge(slide, no: int, y_center_block_top, block_h):
    """번호 배지 — 묶음(block) 세로 중앙에 하나."""
    y = y_center_block_top + (block_h - CIRCLE_D) // 2
    oval = slide.shapes.add_shape(MSO_SHAPE.OVAL, MARGIN_X, y, CIRCLE_D, CIRCLE_D)
    oval.fill.solid()
    oval.fill.fore_color.rgb = RED
    oval.line.fill.background()
    oval.shadow.inherit = False
    tf = oval.text_frame
    _zero_margins(tf)
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _add_run(p, str(no), NUM_PT, WHITE, "Arial", bold=True)


def _draw_sentence(slide, eng: str, kor: str, y, st: dict, pattern=None):
    left = MARGIN_X + CIRCLE_D + TEXT_GAP
    tb = slide.shapes.add_textbox(left, y, PAGE_W - left - MARGIN_X, st["row_h"])
    tf = tb.text_frame
    _zero_margins(tf)
    tf.word_wrap = st["wrap"]
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    if pattern and st["highlight"]:
        for txt, is_pat in _pattern_runs(eng, pattern):
            _add_run(p, txt, st["eng_pt"], BLUE if is_pat else DARK,
                     st["eng_font"], bold=is_pat)
    else:
        _add_run(p, eng, st["eng_pt"], DARK, st["eng_font"], bold=True)
    if kor:
        _add_run(p, f"  -  {kor}", st["kor_pt"], GRAY, KOR_FONT)


def _paginate(items: list, st: dict, max_lines: int) -> list:
    """앞 페이지부터 채운다. 줄 수 상한과 페이지 높이 둘 다 넘지 않게.
    item(번호 묶음)은 분할하지 않는다."""
    usable_h = PAGE_H - TOP - BOTTOM
    pages, cur = [], []
    used_h = used_lines = 0
    for item in items:
        n = len(item["lines"])
        item_h = n * st["row_h"]
        if cur and (used_lines + n > max_lines or used_h + item_h > usable_h):
            pages.append(cur)
            cur, used_h, used_lines = [], 0, 0
        cur.append(item)
        used_lines += n
        used_h += item_h + st["group_gap"]
    if cur:
        pages.append(cur)
    return pages


def build_a4(study: dict, out_path, mode: str = "first",
             max_per_page: int = DEFAULT_MAX_PER_PAGE) -> dict:
    if mode not in MODES:
        raise ValueError(f"지원하지 않는 mode: {mode} (지원: {sorted(MODES)})")
    st = STYLES[mode]
    items = MODES[mode](study["deck"]["rows"])
    if not items:
        raise ValueError("deck.rows 에서 뽑을 예문(line)이 없습니다.")

    prs = Presentation()
    prs.slide_width = PAGE_W
    prs.slide_height = PAGE_H
    blank = prs.slide_layouts[6]

    pages = _paginate(items, st, max_per_page)
    no = 1
    per_page = []
    for page in pages:
        slide = prs.slides.add_slide(blank)
        y = TOP
        n_lines = 0
        for item in page:
            item_h = len(item["lines"]) * st["row_h"]
            _draw_badge(slide, no, y, item_h)
            for eng, kor in item["lines"]:
                _draw_sentence(slide, eng, kor, y, st, pattern=item["pattern"])
                y += st["row_h"]
                n_lines += 1
            y += st["group_gap"]
            no += 1
        per_page.append(n_lines)

    prs.save(str(out_path))
    return {"pptx_path": str(out_path), "mode": mode,
            "n_items": len(items), "n_lines": sum(per_page),
            "pages": len(pages), "per_page": per_page}
