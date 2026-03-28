"""
Theme definitions — colors, fonts, and visual styling.

Each theme is a dict with standardized keys.
Templates reference themes to control appearance.
"""

THEMES = {
    "clean_blue": {
        "name": "简约蓝 (Clean Blue)",
        "colors": {
            "primary": "1A5276",
            "secondary": "5DADE2",
            "background": "FFFFFF",
            "text": "2C3E50",
            "accent": "2E86C1",
            "page_number": "95A5A6"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 32,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": True,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "church_grace": {
        "name": "恩典之光 (Grace)",
        "colors": {
            "primary": "1B4F72",
            "secondary": "7FB3D8",
            "background": "F8F9F9",
            "text": "2C3E50",
            "accent": "2980B9",
            "page_number": "AEB6BF"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 34,
            "body_size": 22,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": False,
            "title_underline": True,
            "slide_number_format": "{current}"
        }
    }
    
    # v0.2
    # "warm_earth": {
    #     "name": "暖色大地 (Warm Earth)",
    #     "colors": {
    #         "primary": "6E2C00",
    #         "secondary": "D35400",
    #         "background": "FEF9E7",
    #         "text": "2C3E50",
    #         "accent": "E67E22",
    #         "page_number": "B7950B"
    #     },
    #     "fonts": {
    #         "title": "Microsoft YaHei",
    #         "body": "Microsoft YaHei",
    #         "title_size": 32,
    #         "body_size": 20,
    #         "page_number_size": 10
    #     },
    #     "decorations": {
    #         "accent_bar": True,
    #         "title_underline": False,
    #         "slide_number_format": "{current} / {total}"
    #     }
    # },
    # "dark_arcade": {
    #     "name": "暗色游戏 (Dark Arcade)",
    #     "colors": {
    #         "primary": "FF6B00",
    #         "secondary": "4ECDC4",
    #         "background": "1A1C29",
    #         "text": "ECEFF1",
    #         "accent": "2F80ED",
    #         "page_number": "78909C"
    #     },
    #     "fonts": {
    #         "title": "Microsoft YaHei",
    #         "body": "Microsoft YaHei",
    #         "title_size": 36,
    #         "body_size": 22,
    #         "page_number_size": 10
    #     },
    #     "decorations": {
    #         "accent_bar": True,
    #         "title_underline": False,
    #         "slide_number_format": "{current} / {total}"
    #     }
    # }
}
