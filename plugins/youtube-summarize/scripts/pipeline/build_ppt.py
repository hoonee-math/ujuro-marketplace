"""범용 덱 렌더러 (수동 레이아웃).

구조(그룹핑·번호·시간 위치)는 AI가 analysis 단계에서 결정한다. 이 렌더러는 덱을 받아 그린다.

레이아웃:
- header 행: 원형 번호 배지(label) + 영어(primary) + 한글(secondary) + 시간([t]) 한 줄.
- line 행: 영어(primary) / 한글(secondary)만 — 번호·시간 없음(헤더에 한 번이면 충분).
- 페이지: 패턴 그룹(header + 그 예문들)을 통째로 배치, 슬라이드 높이를 넘을 때만 그룹 경계에서 분할.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

# 여백 / 크기
LEFT = Inches(0.55)
RIGHT = Inches(0.55)
TOP = Inches(0.5)
BOTTOM = Inches(0.45)
CIRCLE_D = Inches(0.48)
HEADER_TEXT_GAP = Inches(0.18)   # 배지와 헤더 텍스트 사이
LINE_INDENT = Inches(0.5)        # 예문 들여쓰기
HEADER_H = Inches(0.52)
LINE_H = Inches(0.66)            # 영어 + 한글 두 줄
GROUP_GAP = Inches(0.2)

# 폰트 (키움)
HEADER_PRIMARY_PT = 22
HEADER_SECONDARY_PT = 15
HEADER_TIME_PT = 13
BADGE_PT = 17
LINE_PRIMARY_PT = 17
LINE_SECONDARY_PT = 14

NAVY = RGBColor(0x1F, 0x3B, 0x73)
SLATE = RGBColor(0x5B, 0x6B, 0x8C)
INK = RGBColor(0x22, 0x22, 0x22)
GRAY = RGBColor(0x70, 0x70, 0x70)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _groups(rows):
    groups, cur = [], []
    for row in rows:
        if row["kind"] == "header":
            if cur:
                groups.append(cur)
            cur = [row]
        else:
            cur.append(row)
    if cur:
        groups.append(cur)
    return groups


def _group_height(g):
    has_header = g and g[0]["kind"] == "header"
    n_lines = sum(1 for r in g if r["kind"] == "line")
    return (HEADER_H if has_header else 0) + n_lines * LINE_H + GROUP_GAP


def _zero_margins(tf):
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)


def _draw_header(slide, row, y, sw):
    has_badge = bool(row.get("label"))
    text_left = LEFT
    if has_badge:
        oval = slide.shapes.add_shape(MSO_SHAPE.OVAL, LEFT, y, CIRCLE_D, CIRCLE_D)
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

    tb = slide.shapes.add_textbox(text_left, y, sw - text_left - RIGHT, HEADER_H)
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


def _draw_line(slide, row, y, sw):
    left = LEFT + LINE_INDENT
    tb = slide.shapes.add_textbox(left, y, sw - left - RIGHT, LINE_H)
    tf = tb.text_frame
    _zero_margins(tf)
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = row["primary"]
    r.font.size = Pt(LINE_PRIMARY_PT)
    r.font.color.rgb = INK
    if row.get("secondary"):
        p2 = tf.add_paragraph()
        rs = p2.add_run()
        rs.text = row["secondary"]
        rs.font.size = Pt(LINE_SECONDARY_PT)
        rs.font.color.rgb = GRAY
    return y + LINE_H


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


def build_ppt(study: dict, out_path) -> None:
    prs = Presentation()
    sw, sh = prs.slide_width, prs.slide_height
    deck = study["deck"]

    ts = prs.slides.add_slide(prs.slide_layouts[0])
    ts.shapes.title.text = study["source"]["title"]
    ts.placeholders[1].text = deck.get("subtitle") or study["source"].get("channel", "")

    blank = prs.slide_layouts[6]
    usable_h = sh - TOP - BOTTOM
    for page in _paginate(_groups(deck["rows"]), usable_h):
        slide = prs.slides.add_slide(blank)
        y = TOP
        for g in page:
            for row in g:
                if row["kind"] == "header":
                    y = _draw_header(slide, row, y, sw)
                else:
                    y = _draw_line(slide, row, y, sw)
            y += GROUP_GAP
    prs.save(str(out_path))
