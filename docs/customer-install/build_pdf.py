"""Render the Traditional Chinese Markdown guide using ReportLab.

Requires reportlab and a TrueType font with Traditional Chinese glyphs.
No network, global installation or source mutation is performed.
"""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, XPreformatted


ROOT = Path(__file__).resolve().parent


def inline(text):
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font color="#18506d">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r'<b>\1</b>', text)
    def link(match):
        label, url = match.groups()
        if not url.startswith(("https://", "http://")):
            path = (ROOT / url.split("#", 1)[0]).resolve()
            relative = path.relative_to(ROOT.parents[1]).as_posix()
            fragment = "#" + url.split("#", 1)[1] if "#" in url else ""
            url = "https://github.com/codeer-ai/codeer-skills/blob/main/" + relative + fragment
        return f'<link href="{url}" color="#18506d">{label}</link>'
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)


def wrapped_code(lines, width):
    result = []
    for line in lines:
        current = ""
        for character in line:
            if current and pdfmetrics.stringWidth(current + character, "Guide", 8) > width:
                result.append(escape(current))
                current = "    "
            current += character
        result.append(escape(current))
    return "\n".join(result)


def build(source, output):
    width = A4[0] - 38 * mm
    body = ParagraphStyle("body", fontName="Guide", fontSize=10, leading=16,
                          spaceAfter=7, wordWrap="CJK", alignment=TA_LEFT)
    headings = {level: ParagraphStyle(f"h{level}", parent=body, fontName="Guide",
                   fontSize={1: 21, 2: 15, 3: 12}[level], leading={1: 28, 2: 21, 3: 18}[level],
                   textColor=colors.HexColor("#183e50"), spaceBefore=13,
                   spaceAfter=8, keepWithNext=True) for level in (1, 2, 3)}
    code_style = ParagraphStyle("code", parent=body, fontSize=8, leading=12,
                   backColor=colors.HexColor("#f1f5f7"), borderPadding=8,
                   spaceBefore=3, spaceAfter=11)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=11, firstLineIndent=-8)
    lead = ParagraphStyle("lead", parent=body, keepWithNext=True)
    story = []
    lines = source.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if line.startswith("```"):
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            story.append(XPreformatted(wrapped_code(code, width - 16), code_style))
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if not match:
                raise ValueError(f"Unsupported image: {line}")
            picture = Image(str(ROOT / match[2]))
            ratio = min(width / picture.imageWidth, (88 * mm) / picture.imageHeight)
            picture.drawWidth = picture.imageWidth * ratio
            picture.drawHeight = picture.imageHeight * ratio
            story.extend([picture, Spacer(1, 8)])
        elif line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 3)
            story.append(Paragraph(inline(line.lstrip("# ")), headings[level]))
        else:
            is_list = bool(re.match(r"(?:- |\d+\. )", line))
            text = line
            while index < len(lines) and lines[index].strip() and not re.match(r"(?:#|```|!\[|- |\d+\. )", lines[index].strip()):
                text += " " + lines[index].strip()
                index += 1
            style = lead if text in ("可以問：", "執行：") else bullet if is_list else body
            story.append(Paragraph(inline(text), style))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d2dce2"))
        canvas.line(19 * mm, 16 * mm, A4[0] - 19 * mm, 16 * mm)
        canvas.setFont("Guide", 8)
        canvas.setFillColor(colors.HexColor("#526570"))
        canvas.drawString(19 * mm, 11 * mm, "Codeer Agent Skill | 安裝與本機專案指南")
        canvas.drawRightString(A4[0] - 19 * mm, 11 * mm, str(doc.page))
        canvas.restoreState()
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=19 * mm,
                   leftMargin=19 * mm, topMargin=17 * mm, bottomMargin=23 * mm,
                   title="Codeer Agent Skill 客戶安裝指南", author="Codeer.AI")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"))
    parser.add_argument("--source", type=Path, default=ROOT / "customer-install-zh-TW.md")
    parser.add_argument("--output", type=Path, default=ROOT / "customer-install-zh-TW.pdf")
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("Provide --font with a Traditional Chinese TrueType font")
    pdfmetrics.registerFont(TTFont("Guide", str(args.font)))
    pdfmetrics.registerFontFamily("Guide", normal="Guide", bold="Guide", italic="Guide", boldItalic="Guide")
    build(args.source, args.output)


if __name__ == "__main__":
    main()
