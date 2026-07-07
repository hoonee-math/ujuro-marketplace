"""컴팩트 학습 덱 렌더러 — A4 가로, 예문은 '영어 + 한글'을 한 줄에.

classic(build_ppt)과 같은 덱 구조(header/line, 그룹 단위 페이지네이션)를 받아
더 조밀하게 그린다. 같은 페이지에 더 많은 문장이 들어간다.

- 페이지: A4 가로(29.7×21cm) — 화면 학습과 인쇄 양쪽에 적합.
- header: 원형 번호 배지 + 영어 템플릿 + 한국어 뜻 + [시간] 한 줄 (classic 과 동일 구성, 약간 축소).
- line: 영어 원문 바로 뒤에 한글 번역을 같은 줄에 이어 붙인다.
  폭을 넘길 것으로 추정되는 줄만 2줄 높이를 배정한다(word_wrap 허용) —
  추정은 문자폭 휴리스틱(라틴/한글 폭 구분 + 안전여유)이며, 렌더와 페이지네이션이
  같은 추정을 쓰므로 슬라이드↔오디오 구간 매핑이 어긋나지 않는다.
- autoplay 가 슬라이드별 시작 시각을 계산할 수 있도록 content_pages(study) 를 노출한다.
"""
import math

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

from pipeline.build_ppt import _groups

# A4 가로
PAGE_W = Inches(11.69)
PAGE_H = Inches(8.27)

# 여백 / 크기 (classic 보다 조밀)
LEFT = Inches(0.5)
RIGHT = Inches(0.5)
TOP = Inches(0.45)
BOTTOM = Inches(0.4)
CIRCLE_D = Inches(0.4)
HEADER_TEXT_GAP = Inches(0.15)
LINE_INDENT = Inches(0.5)
HEADER_H = Inches(0.46)
LINE_H = Inches(0.34)            # 예문 한 줄(영어+한글) 높이
GROUP_GAP = Inches(0.14)

# 폰트
HEADER_PRIMARY_PT = 19
HEADER_SECONDARY_PT = 13
HEADER_TIME_PT = 11
BADGE_PT = 14
LINE_PRIMARY_PT = 15
LINE_SECONDARY_PT = 12.5

NAVY = RGBColor(0x1F, 0x3B, 0x73)
SLATE = RGBColor(0x5B, 0x6B, 0x8C)
INK = RGBColor(0x22, 0x22, 0x22)
GRAY = RGBColor(0x70, 0x70, 0x70)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# 줄바꿈 추정용 문자폭(인치) — 15pt 라틴 / 12.5pt 한글(전각) / 12.5pt 반각
_W_LAT = 0.100
_W_CJK = 0.170
_W_KOR_NARROW = 0.075
_SAFETY = 1.06                   # 과소추정(다음 줄과 겹침) 방지 여유
_SEP = "   "                     # 영어와 한글 사이 구분 공백


def _text_width_in() -> float:
    return (PAGE_W - LEFT - LINE_INDENT - RIGHT) / 914400


def _line_units(row) -> int:
    """예문 한 줄이 차지할 줄 수(1 또는 2+)를 문자폭 휴리스틱으로 추정."""
    w = len(row["primary"]) * _W_LAT
    kor = row.get("secondary") or ""
    if kor:
        for ch in _SEP + kor:
            w += _W_CJK if ord(ch) > 0x2E80 else _W_KOR_NARROW
    return max(1, math.ceil(w * _SAFETY / _text_width_in()))


def _group_height(g):
    has_header = g and g[0]["kind"] == "header"
    lines_h = sum(_line_units(r) for r in g if r["kind"] == "line") * LINE_H
    return (HEADER_H if has_header else 0) + lines_h + GROUP_GAP


def _paginate(groups, usable_h):
    pages, cur, cur_h = [], [], 0
    for g in groups:
        gh = _group_height(g)
        if cur and cur_h + gh > usable_h:
            pages.append(cur)
            cur, cur_h = [], 0
        cur.append(g)
        cur_h += gh
    if cur:
        pages.append(cur)
    return pages


def content_pages(study: dict):
    """내용 슬라이드별 그룹 목록 — autoplay 의 슬라이드↔구간 매핑용."""
    usable_h = PAGE_H - TOP - BOTTOM
    return _paginate(_groups(study["deck"]["rows"]), usable_h)


def _zero_margins(tf):
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)


def _draw_header(slide, row, y):
    has_badge = bool(row.get("label"))
    text_left = LEFT
    if has_badge:
        oval = slide.shapes.add_shape(MSO_SHAPE.OVAL, LEFT, y + (HEADER_H - CIRCLE_D) // 2,
                                      CIRCLE_D, CIRCLE_D)
        oval.fill.solid()
        oval.fill.fore_color.rgb = NAVY
        oval.line.fill.background()
        oval.shadow.inherit = False
        otf = oval.text_frame
        _zero_margins(otf)
        otf.word_wrap = False
        otf.vertical_anchor = MSO_ANCHOR.MIDDLE
        op = otf.paragraphs[0]
        op.alignment = PP_ALIGN.CENTER
        orun = op.add_run()
        orun.text = str(row["label"])
        orun.font.size = Pt(BADGE_PT)
        orun.font.bold = True
        orun.font.color.rgb = WHITE
        text_left = LEFT + CIRCLE_D + HEADER_TEXT_GAP

    tb = slide.shapes.add_textbox(text_left, y, PAGE_W - text_left - RIGHT, HEADER_H)
    tf = tb.text_frame
    _zero_margins(tf)
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = row["primary"]
    r.font.size = Pt(HEADER_PRIMARY_PT)
    r.font.bold = True
    r.font.color.rgb = NAVY
    if row.get("secondary"):
        r2 = p.add_run()
        r2.text = f"    {row['secondary']}"
        r2.font.size = Pt(HEADER_SECONDARY_PT)
        r2.font.bold = True
        r2.font.color.rgb = SLATE
    if row.get("t"):
        r3 = p.add_run()
        r3.text = f"    [{row['t']}]"
        r3.font.size = Pt(HEADER_TIME_PT)
        r3.font.color.rgb = GRAY
    return y + HEADER_H


def _draw_line(slide, row, y):
    units = _line_units(row)
    h = LINE_H * units
    left = LEFT + LINE_INDENT
    tb = slide.shapes.add_textbox(left, y, PAGE_W - left - RIGHT, h)
    tf = tb.text_frame
    _zero_margins(tf)
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = row["primary"]
    r.font.size = Pt(LINE_PRIMARY_PT)
    r.font.color.rgb = INK
    if row.get("secondary"):
        r2 = p.add_run()
        r2.text = _SEP + row["secondary"]
        r2.font.size = Pt(LINE_SECONDARY_PT)
        r2.font.color.rgb = GRAY
    return y + h


def build_ppt_compact(study: dict, out_path) -> None:
    prs = Presentation()
    prs.slide_width = PAGE_W
    prs.slide_height = PAGE_H
    deck = study["deck"]

    ts = prs.slides.add_slide(prs.slide_layouts[0])
    ts.shapes.title.text = study["source"]["title"]
    ts.placeholders[1].text = deck.get("subtitle") or study["source"].get("channel", "")

    blank = prs.slide_layouts[6]
    for page in content_pages(study):
        slide = prs.slides.add_slide(blank)
        y = TOP
        for g in page:
            for row in g:
                if row["kind"] == "header":
                    y = _draw_header(slide, row, y)
                else:
                    y = _draw_line(slide, row, y)
            y += GROUP_GAP
    prs.save(str(out_path))
