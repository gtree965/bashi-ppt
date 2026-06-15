# Bashi PPT Hymn Lyrics — Language Spec Addendum

> 补充到 Bashi PPT-Hymn-Lyrics-Feature.md
> 覆盖原文档中所有关于「双语模式」的描述

---

## 语言模式设计

### v0.1 支持三种模式

```
模式 1: 纯中文        → 每行统一大字（40pt），白色
模式 2: 纯英文        → 每行统一大字（38pt），白色
模式 3: 中英对照      → 中文主行（36pt）+ 英文副行（28pt 浅色）
```

### v0.2+ 扩展为通用双语对照

```
模式 3 泛化为: 任意「主语言 + 副语言」对照
示例:
  - 中文 + English
  - English + Français
  - 中文 + 한국어
  - English + Español
  - 中文 + Bahasa Indonesia
```

---

## 数据模型修改

### 替换原有 `bilingual: bool` 为结构化语言配置

```python
# v0.1 API 请求格式:

{
  "lyrics": "歌词文本...",
  "title": "奇异恩典",
  "lines_per_slide": 4,
  "theme": "classic_dark",
  "add_title_slide": true,
  "add_amen_slide": true,
  "language_mode": "bilingual",      #  "single" | "bilingual"
  "language_config": {
    "primary": "zh",                  # 主语言代码
    "secondary": "en",                # 副语言代码（仅 bilingual 模式）
    "primary_label": "中文",          # 显示名称
    "secondary_label": "English"
  }
}
```

### v0.1 预设语言选项（前端下拉菜单）

```
[纯中文]           → language_mode: "single", primary: "zh"
[English Only]     → language_mode: "single", primary: "en"
[中文 + English]   → language_mode: "bilingual", primary: "zh", secondary: "en"
```

### v0.2 前端改为自由组合

```
主语言: [中文 ▼]     副语言: [English ▼]

下拉选项:
  中文 (zh)
  English (en)
  Français (fr)
  Español (es)
  한국어 (ko)
  日本語 (ja)
  Bahasa Indonesia (id)
  Português (pt)
  Deutsch (de)
  自定义... (用户输入语言名称)
```

---

## 歌词输入格式

### 单语模式

用户直接粘贴歌词，每行就是一行歌词：

```
Amazing grace, how sweet the sound,
That saved a wretch like me!
I once was lost, but now I'm found,
Was blind, but now I see.
```

### 双语对照模式 — 交替行格式（推荐）

主语言和副语言逐行交替：

```
奇异恩典，何等甘甜，
Amazing grace, how sweet the sound,
我罪已得赦免！
That saved a wretch like me!
前我失丧，今被寻回，
I once was lost, but now I'm found,
瞎眼今得看见。
Was blind, but now I see.
```

### 双语对照模式 — 分段格式（也支持）

先写完一种语言，空行分隔，再写另一种：

```
奇异恩典，何等甘甜，
我罪已得赦免！
前我失丧，今被寻回，
瞎眼今得看见。

Amazing grace, how sweet the sound,
That saved a wretch like me!
I once was lost, but now I'm found,
Was blind, but now I see.
```

---

## 语言检测逻辑

### File: `backend/lyrics/lang_detect.py`

```python
"""
轻量级语言检测 — 不依赖外部库，基于 Unicode 范围判断。

设计原则:
- 不用 langdetect / polyglot 等外部库（减少依赖）
- 只需要区分「哪行是主语言、哪行是副语言」
- 不需要精确识别语种，只需要识别「这行跟上一行是不是同一种语言」
"""

# Unicode 范围参考:
SCRIPT_RANGES = {
    "zh": [
        (0x4E00, 0x9FFF),     # CJK 基本区
        (0x3400, 0x4DBF),     # CJK 扩展 A
        (0xF900, 0xFAFF),     # CJK 兼容
    ],
    "ko": [
        (0xAC00, 0xD7AF),     # 韩文音节
        (0x1100, 0x11FF),     # 韩文字母
    ],
    "ja": [
        (0x3040, 0x309F),     # 平假名
        (0x30A0, 0x30FF),     # 片假名
    ],
    "latin": [
        (0x0041, 0x024F),     # 基本拉丁 + 扩展
    ],
    # 注: 日文也使用汉字，但平假名/片假名是日文独有标志
    # 法文、西班牙文、德文、印尼文、葡萄牙文都属于 latin
}

def classify_line(text: str) -> str:
    """
    判断一行文本的主要文字系统。

    返回: "zh" | "ko" | "ja" | "latin" | "mixed" | "unknown"

    逻辑:
    1. 去除标点和空格
    2. 统计每种文字系统的字符占比
    3. 占比 > 50% 的为主要文字系统
    4. 如果没有明确主导 → "mixed"
    """
    pass

def detect_bilingual_structure(lines: list[str]) -> dict:
    """
    检测歌词的双语结构。

    返回:
    {
        "is_bilingual": True/False,
        "format": "alternating" | "separated" | "none",
        "primary_script": "zh",
        "secondary_script": "latin",
        "line_assignments": [
            {"line": 0, "role": "primary"},
            {"line": 1, "role": "secondary"},
            ...
        ]
    }

    检测逻辑:
    1. 对每行调用 classify_line()
    2. 如果所有行同一文字系统 → not bilingual
    3. 如果奇偶行交替两种文字系统 → alternating
    4. 如果前半段一种、后半段另一种 → separated
    5. primary = 出现更多的那种（或用户指定）
    """
    pass

def pair_bilingual_lines(lines: list[str], structure: dict) -> list[tuple]:
    """
    将双语歌词配对。

    输入: ["奇异恩典", "Amazing grace", "我罪赦免", "saved a wretch"]
    输出: [("奇异恩典", "Amazing grace"), ("我罪赦免", "saved a wretch")]

    交替模式: 直接按奇偶配对
    分段模式: 按行数对半切，逐行配对

    如果两种语言行数不同:
    - 多出的行保留在主语言
    - 副语言缺失的位置留空字符串
    """
    pass
```

---

## 渲染适配

### 单语渲染（不变）

```
每行歌词: 40pt (中文) 或 38pt (英文/拉丁文字)
全部白色，居中
```

### 双语对照渲染

```
主语言行: 36pt, 白色 (#FFFFFF), bold
副语言行: 28pt, 浅灰 (#B0BEC5), regular (not bold)

视觉效果 (以中英为例):

    奇异恩典，何等甘甜，           ← 36pt 白色 粗体
    Amazing grace, how sweet the sound   ← 28pt 浅灰 常规
                                          ← 空行间距
    我罪已得赦免！                 ← 36pt 白色 粗体
    That saved a wretch like me!        ← 28pt 浅灰 常规
```

### 字号自适应

```python
# 不同语言的默认字号建议:
LANGUAGE_FONT_SIZES = {
    # 单语模式
    "single": {
        "zh": 40,     # 汉字方块字，40pt 投影清晰
        "ko": 40,     # 韩文音节类似汉字大小
        "ja": 40,     # 日文同上
        "latin": 38,  # 拉丁字母比汉字窄，可稍大以保持视觉平衡
    },
    # 双语模式 — 主语言
    "bilingual_primary": {
        "zh": 36,
        "ko": 36,
        "ja": 36,
        "latin": 34,
    },
    # 双语模式 — 副语言
    "bilingual_secondary": {
        "zh": 28,
        "ko": 28,
        "ja": 28,
        "latin": 26,
    },
}
```

### 字体适配

```python
# 不同语言的推荐字体:
LANGUAGE_FONTS = {
    "zh": {
        "name": "Microsoft YaHei",
        "east_asian": True,      # 需要设置 a:ea XML 属性
    },
    "ko": {
        "name": "Malgun Gothic",  # Windows 韩文默认字体
        "east_asian": True,
    },
    "ja": {
        "name": "Yu Gothic",     # Windows 日文默认字体
        "east_asian": True,
    },
    "latin": {
        "name": "Arial",         # 通用拉丁字体
        "east_asian": False,
    },
}

# 渲染时根据行的语言分类选择字体:
def get_font_for_line(line_text: str, script: str):
    """返回 (font_name, needs_east_asian_xml)"""
    config = LANGUAGE_FONTS.get(script, LANGUAGE_FONTS["latin"])
    return config["name"], config["east_asian"]
```

---

## 前端 UI 更新

### LyricsInput.jsx — 语言选择器

```jsx
/**
 * 语言模式选择
 *
 * v0.1 界面:
 *
 *   语言模式:
 *     (●) 纯中文
 *     ( ) English Only
 *     ( ) 中文 + English 对照
 *
 * v0.2 界面 (泛化):
 *
 *   语言模式:
 *     (●) 单语
 *     ( ) 双语对照
 *
 *   [单语时显示]
 *     语言: [中文 ▼]
 *
 *   [双语对照时显示]
 *     主语言: [中文 ▼]   副语言: [English ▼]
 *
 *   [自动检测提示]
 *     当用户粘贴歌词后，自动检测语言结构:
 *     "检测到中英交替歌词，已自动切换为双语对照模式"
 */
```

---

## 分页逻辑对双语的影响

双语模式下，「每页行数」的含义发生变化:

```
单语模式:
  lines_per_slide = 4 → 每页显示 4 行歌词

双语对照模式:
  lines_per_slide = 4 → 每页显示 4 个「语言对」= 8 行视觉文本
  这太多了！

所以双语模式需要调整:
  lines_per_slide = 2 → 每页 2 对 = 4 行视觉文本 (推荐)
  lines_per_slide = 3 → 每页 3 对 = 6 行视觉文本 (最大)
```

```python
def calculate_visual_lines(lines_per_slide: int, is_bilingual: bool) -> int:
    """计算每页的视觉行数"""
    if is_bilingual:
        return lines_per_slide * 2  # 每对占 2 行
    return lines_per_slide

# 双语模式默认值:
DEFAULT_LINES_PER_SLIDE = {
    "single": 4,
    "bilingual": 2,  # 2对 = 4行视觉文本
}
```

### 前端对应调整

```
双语对照模式下:
  每页歌词对数: [2] [3] (默认2)
  提示文字: "每页显示2对歌词（共4行）"

单语模式下:
  每页行数: [2] [3] [4] (默认4)
  提示文字: "每页显示4行歌词"
```
