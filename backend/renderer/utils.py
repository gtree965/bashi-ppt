"""
Rendering utilities — shared by presentation renderer and lyrics renderer.

Provides:
  - hex_to_rgb: Convert hex color string to RGBColor
  - set_font: Set font on a text run with proper East Asian XML support
"""

from pptx.dml.color import RGBColor
from pptx.util import Pt
from pptx.oxml.ns import qn


# East Asian scripts that need special XML font attributes
_EAST_ASIAN_SCRIPTS = frozenset({"zh", "ko", "ja"})

# Mapping from script code to default lang attribute
_SCRIPT_LANG_CODES = {
    "zh": "zh-CN",
    "ko": "ko-KR",
    "ja": "ja-JP",
}


def hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert a hex color string (with or without '#') to an RGBColor."""
    hex_str = hex_str.lstrip('#')
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def set_font(
    run,
    font_name: str = "Microsoft YaHei",
    size_pt: int = 20,
    bold: bool = False,
    color: RGBColor | None = None,
    script: str = "zh",
):
    """
    Set font properties on a python-pptx text run.

    For East Asian scripts (zh, ko, ja), also sets the a:ea XML element
    so PowerPoint renders CJK glyphs with the correct typeface.

    Parameters
    ----------
    run : pptx text run
    font_name : font typeface name
    size_pt : font size in points
    bold : whether to bold the text
    color : optional RGBColor
    script : "zh", "ko", "ja", or "latin"
    """
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    if bold:
        run.font.bold = True
    if color is not None:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()

    if script in _EAST_ASIAN_SCRIPTS:
        rPr.set(qn('a:lang'), _SCRIPT_LANG_CODES.get(script, 'zh-CN'))
        ea = rPr.find(qn('a:ea'))
        if ea is None:
            ea = rPr.makeelement(qn('a:ea'), {})
            rPr.append(ea)
        ea.set('typeface', font_name)
