import json
from io import BytesIO
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
import logging

from .theme import THEMES
from .slide_layouts import LAYOUTS, SLIDE_WIDTH, SLIDE_HEIGHT
from .utils import hex_to_rgb, set_font
from config import TEMPLATES_DIR

logger = logging.getLogger("slideforge")


def set_chinese_font(run, font_name="Microsoft YaHei", size_pt=20, bold=False, color: RGBColor = None):
    """Backward-compatible wrapper around set_font for Chinese text."""
    set_font(run, font_name=font_name, size_pt=size_pt, bold=bold, color=color, script="zh")

def estimate_text_height(content_points, font_size_pt, box_width_inches, line_spacing=1.5):
    total_lines = 0
    # Approximate ratio for Chinese chars vs pts.
    chars_per_line = int(box_width_inches * 72 / font_size_pt) 

    for point in content_points:
        lines_needed = max(1, -(-len(point) // chars_per_line)) if chars_per_line > 0 else 1
        total_lines += lines_needed

    height_inches = total_lines * font_size_pt * line_spacing / 72
    return height_inches

def _fit_text_in_box(max_height_inches, box_width_inches, content_points, base_font_size=20, min_font_size=14):
    font_size = base_font_size
    line_spacing = 1.5
    points = content_points.copy()
    layout_warning = False

    while font_size >= min_font_size:
        if estimate_text_height(points, font_size, box_width_inches, line_spacing) <= max_height_inches:
            return font_size, line_spacing, points, layout_warning
        font_size -= 2

    # Still overflowing at min size, try reducing spacing
    line_spacing = 1.2
    if estimate_text_height(points, font_size, box_width_inches, line_spacing) <= max_height_inches:
        return font_size, line_spacing, points, layout_warning

    # Still overflowing, truncate text
    layout_warning = True
    while points and estimate_text_height(points, font_size, box_width_inches, line_spacing) > max_height_inches:
        if len(points[-1]) > 5:
            points[-1] = points[-1][:-5] + "..."
        else:
            points.pop()
            
    return font_size, line_spacing, points, layout_warning

class PPTXRenderer:
    def __init__(self, template_id: str):
        self.template_id = template_id
        template_path = TEMPLATES_DIR / f"{template_id}.json"
        
        if not template_path.exists():
            template_path = TEMPLATES_DIR / "teaching.json"
            
        with open(template_path, 'r', encoding='utf-8') as f:
            self.template_config = json.load(f)
            
        theme_id = self.template_config.get("theme", "clean_blue")
        self.theme = THEMES.get(theme_id, THEMES["clean_blue"])
        self.layout_mapping = self.template_config.get("layout_mapping", {})
        
        self.colors = self.theme["colors"]
        self.fonts = self.theme["fonts"]
        self.decorations = self.theme["decorations"]

    def render(self, outline: dict) -> bytes:
        prs = Presentation()
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT
        
        slides_data = outline.get("slides", [])
        total_slides = len(slides_data)
        
        for idx, slide_data in enumerate(slides_data):
            self._render_slide(prs, slide_data, idx + 1, total_slides)
            
        buffer = BytesIO()
        prs.save(buffer)
        return buffer.getvalue()
        
    def _create_blank_slide(self, prs):
        # Index 6 is typically 'Blank'
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        
        background = slide.background
        fill = background.fill
        fill.solid()
        bg_color = hex_to_rgb(self.colors["background"])
        fill.fore_color.rgb = bg_color
        return slide

    def _render_slide(self, prs, slide_data: dict, current: int, total: int):
        slide_type = slide_data.get("slide_type", "content")
        layout_id = self.layout_mapping.get(slide_type)
        if slide_type == "title":
            layout_id = layout_id or "TitleCenterLayout"
            self._render_title_slide(prs, slide_data, layout_id, current, total)
        elif slide_type == "conclusion":
            layout_id = layout_id or "ConclusionLayout"
            self._render_conclusion_slide(prs, slide_data, layout_id, current, total)
        else:
            layout_id = layout_id or "ContentBulletLayout"
            self._render_content_slide(prs, slide_data, layout_id, current, total)
            
    def _render_title_slide(self, prs, slide_data: dict, layout_id: str, current: int, total: int):
        slide = self._create_blank_slide(prs)
        layout = LAYOUTS.get(layout_id, LAYOUTS["TitleCenterLayout"])
        
        # Title
        t_box = layout["title_box"]
        txBox = slide.shapes.add_textbox(t_box["left"], t_box["top"], t_box["width"], t_box["height"])
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = slide_data.get("title", "")
        set_chinese_font(run, font_name=self.fonts["title"], size_pt=self.fonts.get("title_size", 44), 
                         bold=True, color=hex_to_rgb(self.colors["primary"]))
                         
        # Subtitle (Points)
        points = slide_data.get("content_points", [])
        if points:
            s_box = layout["subtitle_box"]
            sxBox = slide.shapes.add_textbox(s_box["left"], s_box["top"], s_box["width"], s_box["height"])
            sf = sxBox.text_frame
            sf.word_wrap = True
            p = sf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = "\n".join(points)
            set_chinese_font(run, font_name=self.fonts["body"], size_pt=self.fonts.get("body_size", 20), 
                             color=hex_to_rgb(self.colors["secondary"]))

        # Decorative line
        if self.decorations.get("title_underline", False) and "accent_line" in layout:
            line_box = layout["accent_line"]
            shape = slide.shapes.add_shape(
                1, # MSO_SHAPE.RECTANGLE
                line_box["left"], line_box["top"], line_box["width"], line_box["height"]
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb(self.colors["accent"])
            shape.line.fill.background()
            
    def _render_content_slide(self, prs, slide_data: dict, layout_id: str, current: int, total: int):
        slide = self._create_blank_slide(prs)
        layout = LAYOUTS.get(layout_id, LAYOUTS["ContentBulletLayout"])
        
        # Title
        t_box = layout["title_box"]
        txBox = slide.shapes.add_textbox(t_box["left"], t_box["top"], t_box["width"], t_box["height"])
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = slide_data.get("title", "")
        set_chinese_font(run, font_name=self.fonts["title"], size_pt=self.fonts.get("title_size", 32), 
                         bold=True, color=hex_to_rgb(self.colors["primary"]))
                         
        # Points
        points = slide_data.get("content_points", [])
        c_box = layout["content_box"]
        
        # Calculate overflow
        box_w = c_box["width"].inches
        box_h = c_box["height"].inches
        f_size, line_spacing, fitted_points, layout_warning = _fit_text_in_box(
            box_h, box_w, points, base_font_size=self.fonts.get("body_size", 20)
        )
        if layout_warning:
            logger.warning(f"Text overflow on slide {current}, truncated content.")
            
        if fitted_points:
            cxBox = slide.shapes.add_textbox(c_box["left"], c_box["top"], c_box["width"], c_box["height"])
            cf = cxBox.text_frame
            cf.word_wrap = True
            
            for i, point in enumerate(fitted_points):
                p = cf.paragraphs[0] if i == 0 else cf.add_paragraph()
                p.text = point
                p.level = 0
                p.line_spacing = line_spacing
                p.space_after = Pt(8)
                run = p.runs[0] if p.runs else p.add_run()
                if not p.runs:
                    run.text = point
                set_chinese_font(run, font_name=self.fonts["body"], size_pt=f_size, 
                                 color=hex_to_rgb(self.colors["text"]))

        # Optional accent bar
        if self.decorations.get("accent_bar", False) and "accent_bar" in layout:
            bar_box = layout["accent_bar"]
            shape = slide.shapes.add_shape(
                1, # MSO_SHAPE.RECTANGLE
                bar_box["left"], bar_box["top"], bar_box["width"], bar_box["height"]
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = hex_to_rgb(self.colors["primary"])
            shape.line.fill.background()

        # Page Number
        self._add_slide_number(slide, layout, current, total)
        
    def _render_conclusion_slide(self, prs, slide_data: dict, layout_id: str, current: int, total: int):
        slide = self._create_blank_slide(prs)
        layout = LAYOUTS.get(layout_id, LAYOUTS["ConclusionLayout"])
        
        # Title
        t_box = layout["title_box"]
        txBox = slide.shapes.add_textbox(t_box["left"], t_box["top"], t_box["width"], t_box["height"])
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = slide_data.get("title", "")
        set_chinese_font(run, font_name=self.fonts["title"], size_pt=self.fonts.get("title_size", 44), 
                         bold=True, color=hex_to_rgb(self.colors["primary"]))

        # Points
        points = slide_data.get("content_points", [])
        if points:
            p_box = layout["points_box"]
            pxBox = slide.shapes.add_textbox(p_box["left"], p_box["top"], p_box["width"], p_box["height"])
            pf = pxBox.text_frame
            pf.word_wrap = True
            for i, point in enumerate(points):
                p = pf.paragraphs[0] if i == 0 else pf.add_paragraph()
                p.text = point
                p.level = 0
                p.alignment = PP_ALIGN.CENTER
                run = p.runs[0] if p.runs else p.add_run()
                if not p.runs:
                    run.text = point
                set_chinese_font(run, font_name=self.fonts["body"], size_pt=self.fonts.get("body_size", 20), 
                                 color=hex_to_rgb(self.colors["secondary"]))

    def _add_slide_number(self, slide, layout, current: int, total: int):
        if "page_number" not in layout:
            return
            
        fmt = self.decorations.get("slide_number_format", "{current}")
        text = fmt.format(current=current, total=total)
        
        num_box = layout["page_number"]
        bxBox = slide.shapes.add_textbox(num_box["left"], num_box["top"], num_box["width"], num_box["height"])
        tf = bxBox.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        set_chinese_font(run, font_name=self.fonts.get("body", "Arial"), size_pt=self.fonts.get("page_number_size", 10), 
                         color=hex_to_rgb(self.colors["page_number"]))
