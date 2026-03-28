"""
Slide layout strategies.
Defines the WHERE elements go on the slide using Inches.
Templates define HOW they look (colors, fonts, sizes).
"""

from pptx.util import Inches

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

LAYOUTS = {
    "TitleCenterLayout": {
        "title_box": {"left": Inches(1.0), "top": Inches(2.0), "width": Inches(11.333), "height": Inches(1.5)},
        "subtitle_box": {"left": Inches(2.0), "top": Inches(4.0), "width": Inches(9.333), "height": Inches(2.0)},
        "accent_line": {"left": Inches(5.0), "top": Inches(3.7), "width": Inches(3.333), "height": Inches(0.02)}
    },
    "ContentBulletLayout": {
        "title_box": {"left": Inches(0.8), "top": Inches(0.4), "width": Inches(11.733), "height": Inches(0.9)},
        "content_box": {"left": Inches(1.0), "top": Inches(1.6), "width": Inches(11.333), "height": Inches(5.2)},
        "page_number": {"left": Inches(12.0), "top": Inches(7.0), "width": Inches(1.0), "height": Inches(0.3)},
        "accent_bar": {"left": Inches(0.0), "top": Inches(0.4), "width": Inches(0.15), "height": Inches(0.9)}
    },
    "ConclusionLayout": {
        "title_box": {"left": Inches(1.0), "top": Inches(1.5), "width": Inches(11.333), "height": Inches(1.5)},
        "points_box": {"left": Inches(2.0), "top": Inches(3.5), "width": Inches(9.333), "height": Inches(3.0)}
    }
}
