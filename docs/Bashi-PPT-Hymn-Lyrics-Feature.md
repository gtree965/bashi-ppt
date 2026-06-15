# Bashi PPT — Hymn Lyrics Feature Spec
## 赞美诗歌词 PPT 生成模块

> 这是 Bashi PPT v0.2 的核心新功能。
> 与大纲生成不同，此功能完全不需要 LLM 调用。
> 纯文本解析 + python-pptx 渲染。

---

## 1. 用户需求场景

### 当前痛点
教会敬拜需要在投影上显示歌词。现有流程：
1. 上网搜索歌曲的官方 PPT（经常找不到或质量差）
2. 如果没有，手动在 PowerPoint 里逐页输入歌词
3. 调整每页行数（太多看不清，太少翻页太快）
4. 调配色、字号、背景
5. 一首歌可能花费 15-30 分钟

### Bashi PPT 解决方案
1. 粘贴歌词原文（或从文件导入）
2. 系统自动识别段落（主歌、副歌、桥段）
3. 自动分页（每页 2-4 行，适合投影阅读）
4. 一键生成深色背景 + 大字居中的 PPTX
5. 整个过程：30 秒内完成

---

## 2. 工作流设计

```
┌─────────────────────────────────┐
│  歌词输入页面                     │
│                                  │
│  ┌────────────────────────────┐  │
│  │  粘贴歌词 (textarea)        │  │
│  │                            │  │
│  │  奇异恩典，何等甘甜，         │  │
│  │  我罪已得赦免！              │  │
│  │  前我失丧，今被寻回，         │  │
│  │  瞎眼今得看见。              │  │
│  │                            │  │
│  │  如此恩典，使我敬畏，         │  │
│  │  使我心得安慰；              │  │
│  │  初信之时，即蒙恩惠，         │  │
│  │  真是何等宝贵！              │  │
│  │  ...                       │  │
│  └────────────────────────────┘  │
│                                  │
│  歌曲标题: [奇异恩典____________]  │
│  每页行数: [2] [3] [4] (默认4)    │
│  样式:     [经典黑底白字]         │
│            [深蓝渐变]            │
│            [自定义纯色]           │
│                                  │
│  [ ] 双语模式 (中文+英文交替)      │
│  [ ] 添加标题页                   │
│  [ ] 添加结尾页 (阿们)            │
│                                  │
│       [✨ 生成歌词 PPT]           │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  预览 & 调整                     │
│                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐     │
│  │第1页  │ │第2页  │ │第3页  │    │
│  │      │ │      │ │      │     │
│  │奇异恩典│ │如此恩典│ │许多危险│   │
│  │何等甘甜│ │使我敬畏│ │试炼网罗│   │
│  │我罪已得│ │使我心得│ │我已安然│   │
│  │赦免！  │ │安慰；  │ │经过   │   │
│  └──────┘ └──────┘ └──────┘     │
│                                  │
│  点击任意页可调整分页位置           │
│                                  │
│       [📥 下载 PPTX]             │
└─────────────────────────────────┘
```

---

## 3. 歌词解析引擎

### File: `backend/lyrics/parser.py`

```python
"""
Lyrics Parser — 将原始歌词文本解析为结构化数据。

输入: 用户粘贴的歌词原文（纯文本）
输出: 分段、分页后的歌词结构

解析规则:
1. 空行分割 → 段落（verse/chorus/bridge）
2. 连续非空行 → 同一段落内的歌词行
3. 自动识别标记:
   - "副歌" / "chorus" / "※" → 标记为 chorus
   - "桥段" / "bridge" → 标记为 bridge
   - "(x2)" / "(重复)" → 标记需要重复
4. 去除行首行尾空白
5. 去除空段落
"""

# 核心数据结构:

class LyricLine:
    text: str           # "奇异恩典，何等甘甜，"
    is_chorus: bool     # 是否属于副歌
    language: str       # "zh" | "en" | "both"

class LyricSection:
    section_type: str   # "verse" | "chorus" | "bridge" | "intro" | "outro"
    lines: list[LyricLine]
    repeat_count: int   # 默认 1

class LyricDocument:
    title: str
    sections: list[LyricSection]
    total_lines: int

# 实现要求:

def parse_lyrics(raw_text: str) -> LyricDocument:
    """
    Step 1: 按空行分割段落
    Step 2: 检测每段是否有标记词（副歌/chorus/※等）
    Step 3: 每段内按换行符分割为行
    Step 4: 检测双语模式（中英文交替行）
    Step 5: 返回 LyricDocument
    """
    pass

def split_into_slides(doc: LyricDocument, lines_per_slide: int = 4) -> list[list[str]]:
    """
    将歌词按指定行数分页。

    关键规则:
    - 尽量不在段落中间分页（保持一个verse完整）
    - 如果一个段落超过 lines_per_slide，才在段落内分割
    - 副歌段落重复时，每次重复都生成新页面
    - 短段落（≤2行）可以和下一段合并到同一页
    - 最后一页如果只有1行，合并到前一页

    示例 (lines_per_slide=4):
    输入: 段落1(4行) + 段落2(4行) + 段落3(2行)
    输出: [页1: 段落1全部] [页2: 段落2全部] [页3: 段落3 + 可能合并]
    """
    pass
```

### 双语歌词检测逻辑

```python
def detect_bilingual(lines: list[str]) -> bool:
    """
    检测是否为中英双语歌词。

    常见格式:
    A) 交替行（最常见）:
       奇异恩典，何等甘甜，
       Amazing grace, how sweet the sound,
       我罪已得赦免！
       That saved a wretch like me!

    B) 段落分隔:
       [中文]
       奇异恩典，何等甘甜，
       我罪已得赦免！

       [English]
       Amazing grace, how sweet the sound,
       That saved a wretch like me!

    检测方法:
    - 统计每行的 Unicode 范围
    - 如果中文行和英文行交替出现 → 交替模式
    - 如果前半部分全中文、后半部分全英文 → 段落分隔模式
    """
    pass
```

---

## 4. 歌词渲染引擎

### File: `backend/lyrics/renderer.py`

```python
"""
Lyrics PPTX Renderer — 专为敬拜投影优化的渲染器。

与普通 PPT 渲染器的关键区别:
1. 文字必须非常大（投影仪 + 后排会众）
2. 背景必须深色（减少投影仪光污染）
3. 文字居中（水平 + 垂直）
4. 每页内容极简（只有歌词，无标题栏/页码）
5. 无项目符号（歌词不用 bullet points）
6. 行间距要宽（方便跟唱）
"""

# 渲染规格:

LYRICS_SLIDE_SPEC = {
    "slide_width": 13.333,    # inches (16:9)
    "slide_height": 7.5,      # inches

    # 歌词文本框（居中，留边距）
    "text_box": {
        "x": 1.0,             # inches from left
        "y": 1.0,             # inches from top
        "width": 11.333,      # inches
        "height": 5.5,        # inches
    },

    # 字体设置
    "font": {
        "name": "Microsoft YaHei",
        "size_zh": 40,        # pt — 中文歌词（大屏投影需要大字）
        "size_en": 36,        # pt — 英文歌词（英文字母比汉字窄，可稍大）
        "size_bilingual_zh": 36,  # 双语模式中文（略小以留空间）
        "size_bilingual_en": 28,  # 双语模式英文（明显小于中文）
        "bold": True,
        "line_spacing": 1.5,  # 行间距倍数
    },

    # 文字对齐
    "alignment": "center",    # 水平居中
    "vertical_anchor": "middle",  # 垂直居中

    # 标题页（可选）
    "title_slide": {
        "title_size": 54,     # pt
        "subtitle_size": 24,  # pt — 用于显示作词作曲信息
    },
}

# 歌词主题:

LYRICS_THEMES = {
    "classic_dark": {
        "name": "经典黑底白字",
        "background": "000000",    # 纯黑
        "text_color": "FFFFFF",    # 纯白
        "chorus_color": "FFD700",  # 金色（副歌高亮）
    },
    "deep_blue": {
        "name": "深蓝渐变",
        "background_gradient": {
            "start": "0C1445",     # 深海蓝
            "end": "1A237E",       # 靛蓝
        },
        "text_color": "FFFFFF",
        "chorus_color": "81D4FA",  # 浅蓝（副歌高亮）
    },
    "warm_dark": {
        "name": "暖色深底",
        "background": "1A0A00",    # 深棕黑
        "text_color": "FFF8E1",    # 暖白
        "chorus_color": "FFB74D",  # 暖橙（副歌高亮）
    },
}
```

### 渲染逻辑

```python
class LyricsPPTXRenderer:
    """
    生成敬拜用歌词 PPTX。

    与通用 PPT 渲染器完全独立——不复用 renderer/engine.py。
    原因: 歌词 PPT 的排版规则与演示文稿完全不同:
    - 无标题栏
    - 无项目符号
    - 纯居中大字
    - 深色背景
    - 可选背景图片
    """

    def render(self, slides_data: list[list[str]],
               title: str = "",
               theme: str = "classic_dark",
               add_title_slide: bool = True,
               add_amen_slide: bool = True,
               bilingual: bool = False) -> bytes:
        """
        slides_data: 分页后的歌词，每个元素是一页的行列表
                     例: [["奇异恩典，何等甘甜，", "我罪已得赦免！"],
                          ["前我失丧，今被寻回，", "瞎眼今得看见。"]]

        返回: PPTX 文件的 bytes
        """
        pass

    def _render_title_slide(self, prs, title, theme_config):
        """
        标题页: 歌曲名称居中大字
        可选: 作词/作曲/来源信息
        """
        pass

    def _render_lyrics_slide(self, prs, lines, theme_config, is_chorus=False):
        """
        歌词页: 每行歌词居中显示
        副歌行使用 chorus_color 高亮

        垂直居中技巧:
        python-pptx 不直接支持文本框垂直居中。
        使用: text_frame.paragraphs 设置后，
        通过 txBody XML 设置 anchor="ctr"

        from pptx.oxml.ns import qn
        txBody = text_box.text_frame._txBody
        bodyPr = txBody.find(qn('a:bodyPr'))
        bodyPr.set('anchor', 'ctr')
        """
        pass

    def _render_amen_slide(self, prs, theme_config):
        """
        结尾页: 显示 "阿们" 或 "Amen"
        使用与歌词相同的样式，但字号更大
        """
        pass

    def _render_bilingual_slide(self, prs, zh_lines, en_lines, theme_config):
        """
        双语歌词页:
        中文行: 较大字号 (36pt)，白色
        英文行: 较小字号 (28pt)，稍暗颜色
        交替排列:

        奇异恩典，何等甘甜，          ← 36pt 白色
        Amazing grace, how sweet the sound  ← 28pt 浅灰
        我罪已得赦免！                ← 36pt 白色
        That saved a wretch like me!     ← 28pt 浅灰
        """
        pass
```

---

## 5. API 路由

```python
# 新增路由到 backend/app.py

# POST /api/generate-lyrics-pptx
# Request body:
# {
#   "lyrics": "奇异恩典，何等甘甜，\n我罪已得赦免！\n...",
#   "title": "奇异恩典",
#   "lines_per_slide": 4,
#   "theme": "classic_dark",
#   "add_title_slide": true,
#   "add_amen_slide": true,
#   "bilingual": false
# }
# Response: PPTX file stream (same as generate-pptx)

# POST /api/preview-lyrics
# Request body: same as above
# Response:
# {
#   "success": true,
#   "slides": [
#     { "page": 1, "type": "title", "content": "奇异恩典" },
#     { "page": 2, "type": "lyrics", "lines": ["奇异恩典，何等甘甜，", "我罪已得赦免！", ...] },
#     ...
#   ],
#   "total_pages": 8
# }
# 用于前端预览分页效果，用户可以调整 lines_per_slide 后重新预览
```

---

## 6. 前端组件

### File: `frontend/src/components/LyricsInput.jsx`

```jsx
/**
 * 歌词输入页面
 *
 * 布局:
 * - 大文本框 (textarea): 至少 12 行高，等宽字体方便对齐
 * - 歌曲标题输入框
 * - 每页行数选择器: 2 / 3 / 4 (radio buttons, 默认 4)
 * - 样式选择器: 3 个主题的色块预览
 * - 复选框: 双语模式 / 添加标题页 / 添加结尾页(阿们)
 * - "预览分页" 按钮 → 调用 /api/preview-lyrics
 * - "生成 PPT" 按钮 → 调用 /api/generate-lyrics-pptx
 *
 * UX 细节:
 * - textarea 的 placeholder 显示一首示例歌词
 * - 粘贴歌词后自动检测是否双语，自动勾选
 * - 每页行数改变时自动刷新预览
 */
```

### File: `frontend/src/components/LyricsPreview.jsx`

```jsx
/**
 * 歌词分页预览
 *
 * 显示效果:
 * - 水平滚动的缩略图卡片
 * - 每张卡片模拟深色背景 + 白色歌词的效果
 * - 当前选中的卡片高亮
 * - 卡片底部显示页码
 *
 * 可选交互 (v0.2):
 * - 点击卡片之间的位置，手动调整分页点
 * - 拖拽卡片边界来合并或拆分页面
 *
 * v0.1 只需要:
 * - 显示分页结果
 * - 允许调整"每页行数"后重新预览
 */
```

---

## 7. 前端导航更新

Bashi PPT 现在有两个主要功能入口:

```jsx
/**
 * App.jsx — 更新为双模式入口
 *
 * 顶部: 模式切换标签
 *   [📊 演示文稿 PPT]  [🎵 赞美诗歌词 PPT]
 *
 * 选择"演示文稿"→ 原有三步向导 (Topic → Outline → Generate)
 * 选择"赞美诗歌词"→ 歌词模式 (Paste → Preview → Generate)
 *
 * 两个模式共享:
 * - Flask API 后端
 * - 下载逻辑
 * - Header 组件
 *
 * 两个模式独立:
 * - 输入组件不同
 * - 渲染器不同 (engine.py vs lyrics/renderer.py)
 * - 主题系统不同 (演示主题 vs 歌词主题)
 */
```

---

## 8. 测试歌词样本

### 测试 1: 简单中文 (4段，每段4行)

```
奇异恩典，何等甘甜，
我罪已得赦免！
前我失丧，今被寻回，
瞎眼今得看见。

如此恩典，使我敬畏，
使我心得安慰；
初信之时，即蒙恩惠，
真是何等宝贵！

许多危险，试炼网罗，
我已安然经过；
靠主恩典，安全不怕，
更引导我归家。

将来禧年，圣徒欢聚，
恩光爱谊千年；
喜乐颂赞，在父座前，
好像初蒙恩典。
```

预期结果: 4页 (每页1段=4行) + 可选标题页 + 可选阿们页 = 4-6页

### 测试 2: 中英双语 (交替行)

```
奇异恩典，何等甘甜，
Amazing grace, how sweet the sound,
我罪已得赦免！
That saved a wretch like me!
前我失丧，今被寻回，
I once was lost, but now I'm found,
瞎眼今得看见。
Was blind, but now I see.

如此恩典，使我敬畏，
'Twas grace that taught my heart to fear,
使我心得安慰；
And grace my fears relieved.
初信之时，即蒙恩惠，
How precious did that grace appear,
真是何等宝贵！
The hour I first believed.
```

预期结果 (lines_per_slide=4, bilingual=true):
- 每页显示 2 对中英文 (4行视觉，但语义上是2句)
- 中文大字 + 英文小字交替

### 测试 3: 有副歌标记

```
有一位神，有权能创造宇宙万物，
也有温柔双手安慰受伤灵魂，
谁能描写，谁能述说，
祂的奇妙、祂的伟大。

副歌:
有一位神，有权能创造宇宙万物，
也有温柔双手安慰受伤灵魂。

有一位神，掌管浩瀚无穷宇宙，
却用全心全意来爱我们每个人，
不分种族、不分贫富，
一律平等对待。

副歌:
有一位神，有权能创造宇宙万物，
也有温柔双手安慰受伤灵魂。
```

预期结果:
- 副歌行使用金色/高亮色
- 副歌每次出现都生成独立页面（不去重）

---

## 9. 开发优先级

```
这个功能比演示文稿模式简单得多，因为:
- 零 LLM 调用（纯文本处理）
- 零网络依赖（不需要图片搜索）
- 布局简单（每页只有居中文字）
- 字体固定（不需要多种字体组合）

估算工作量:
  lyrics/parser.py:      4-6 小时
  lyrics/renderer.py:    4-6 小时
  前端 LyricsInput:      3-4 小时
  前端 LyricsPreview:    3-4 小时
  API 路由 + 集成:       2 小时
  测试 + 调试:           3-4 小时
  ────────────────────────────
  总计:                  ~20-24 小时（约3天业余时间）
```

---

## 10. 与现有架构的关系

```
Bashi PPT/
├── backend/
│   ├── app.py                    # 新增 2 个路由
│   ├── schema.py                 # 不变
│   ├── llm/                      # 歌词模式不使用
│   ├── renderer/                 # 演示文稿渲染器（不变）
│   │
│   ├── lyrics/                   # ← 新增目录
│   │   ├── __init__.py
│   │   ├── parser.py             # 歌词解析
│   │   └── renderer.py           # 歌词 PPTX 渲染
│   │
│   └── templates/                # 不变
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # 添加模式切换
│   │   ├── components/
│   │   │   ├── TopicInput.jsx    # 不变
│   │   │   ├── OutlineEditor.jsx # 不变
│   │   │   ├── LyricsInput.jsx   # ← 新增
│   │   │   └── LyricsPreview.jsx # ← 新增
```

歌词模块完全独立，不影响现有演示文稿功能。
共用 Flask 后端、下载逻辑、前端框架。
不共用渲染器（歌词排版规则完全不同）。
