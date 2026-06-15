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
    },
    
    "warm_earth": {
        "name": "暖色大地 (Warm Earth)",
        "colors": {
            "primary": "6E2C00",
            "secondary": "D35400",
            "background": "FEF9E7",
            "text": "2C3E50",
            "accent": "E67E22",
            "page_number": "B7950B"
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
            "title_underline": False,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "dark_arcade": {
        "name": "暗色游戏 (Dark Arcade)",
        "colors": {
            "primary": "FF6B00",
            "secondary": "4ECDC4",
            "background": "1A1C29",
            "text": "ECEFF1",
            "accent": "2F80ED",
            "page_number": "78909C"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 36,
            "body_size": 22,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": False,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "emerald_growth": {
        "name": "翡翠生机 (Emerald Growth)",
        "colors": {
            "primary": "0E6251",
            "secondary": "1E8449",
            "background": "E8F8F5",
            "text": "1A252C",
            "accent": "117A65",
            "page_number": "1E8449"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 34,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": True,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "royal_purple": {
        "name": "皇家紫韵 (Royal Purple)",
        "colors": {
            "primary": "5B2C6F",
            "secondary": "884EA0",
            "background": "F4ECF7",
            "text": "2C3E50",
            "accent": "AF7AC5",
            "page_number": "884EA0"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 34,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": False,
            "title_underline": True,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "sleek_dark": {
        "name": "极简暗黑 (Sleek Dark)",
        "colors": {
            "primary": "D4AC0D",
            "secondary": "17A589",
            "background": "121212",
            "text": "ECEFF1",
            "accent": "F39C12",
            "page_number": "7F8C8D"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 36,
            "body_size": 22,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": False,
            "slide_number_format": "{current} / {total}"
        }
    },
    
    "cherry_blossom": {
        "name": "樱花粉黛 (Cherry Blossom)",
        "colors": {
            "primary": "78281F",
            "secondary": "CB4335",
            "background": "FDEDEC",
            "text": "2C3E50",
            "accent": "EC7063",
            "page_number": "CB4335"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 34,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": True,
            "slide_number_format": "{current} / {total}"
        }
    }
}
