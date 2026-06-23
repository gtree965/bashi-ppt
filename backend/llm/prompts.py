"""
Prompt templates for outline generation.

Design goals:
- Keep the system prompt compact for local 4B models
- Generate prompt rules directly from schema.py constraints
- Force JSON-only output and forbid chart/image metadata
- Allow optional pasted reference text without bloating the prompt too far
"""

import json
from typing import Literal

from schema import OUTLINE_CONSTRAINTS, SLIDE_CONSTRAINTS
from text_constraints import limit_description

SCENARIO_HINTS = {
    "teaching": "面向课堂教学，语言清楚、适合学生理解。",
    "church": "面向教会讲座或主日学，语气温和、内容尊重信仰语境。",
    "parents": "面向家长说明会，强调价值、方法与沟通。",
    "general": "面向通用演示，结构清楚、表达自然。",
}

LANGUAGE_HINTS = {
    "zh": "全部内容使用简体中文。",
    "en": "All content must be in natural English.",
    "bilingual": "所有标题和要点都必须同时包含简体中文与自然英文，并保持简洁。",
}

REFERENCE_TEXT_PROMPT_LIMIT = 5000

# Product modes. Historical ``legacy`` comparisons are isolated behind
# ``build_legacy_experiment_messages`` and are not accepted by the product API.
GenerationMode = Literal["creative", "grounded"]


def build_system_prompt(
    mode: GenerationMode = "creative",
    output_language: str = "zh",
) -> str:
    """Build the compact system prompt from shared schema constraints."""
    title_constraints = SLIDE_CONSTRAINTS["title"]
    content_constraints = SLIDE_CONSTRAINTS["content"]
    conclusion_constraints = SLIDE_CONSTRAINTS["conclusion"]
    content_min_points = 1 if mode == "grounded" else 3

    return (
        "你是巴适PPT的大纲生成助手。根据用户主题生成演示文稿大纲。\n"
        "严格要求：\n"
        "1. 只输出合法JSON，不要Markdown，不要解释。\n"
        "2. 顶层格式必须是 "
        '{"title":"演示标题","slides":[{"page_number":1,"title":"页面标题","content_points":["要点1","要点2"],"slide_type":"title"}]}。\n'
        "其中 content_points 必须是包含多个独立字符串的 JSON 数组，绝对不能合并为一个带换行符的单字符串。\n"
        f"3. 总页数必须在{OUTLINE_CONSTRAINTS['min_slides']}-{OUTLINE_CONSTRAINTS['max_slides']}之间。\n"
        "4. 结构必须是：第一页title，中间全部是content，最后一页conclusion。\n"
        f"5. 标题页：{title_constraints['min_points']}-{title_constraints['max_points']}个要点，"
        f"每点不超过{limit_description(title_constraints['max_point_length'], output_language)}，"
        f"页标题不超过{limit_description(title_constraints['max_title_length'], output_language)}。\n"
        f"6. 内容页：{content_min_points}-{content_constraints['max_points']}个要点，"
        f"每点不超过{limit_description(content_constraints['max_point_length'], output_language)}，"
        f"页标题不超过{limit_description(content_constraints['max_title_length'], output_language)}。\n"
        f"7. 总结页：{conclusion_constraints['min_points']}-{conclusion_constraints['max_points']}个要点，"
        f"每点不超过{limit_description(conclusion_constraints['max_point_length'], output_language)}，"
        f"页标题不超过{limit_description(conclusion_constraints['max_title_length'], output_language)}。\n"
        "8. page_number 必须从1开始连续编号。\n"
        "9. 不要生成chart_config、image_config、description或type字段。\n"
        "10. 仅在内容页（content），当某页适合用流程图、关系图或步骤图来解释时，"
        "可以可选地添加一个 diagram 字段，值为合法的 Mermaid 代码。"
        "图示会放在幻灯片右侧较窄的竖向区域，请优先使用自上而下的纵向布局"
        '（例如 "flowchart TD; A[输入]-->B[处理]-->C[输出]"），避免过宽的横向（LR）布局。'
        "节点文字要简短。若该页不需要图示，则省略 diagram 字段。标题页和总结页不要加 diagram。\n"
        "11. 内容要贴合主题，顺序自然，适合目标受众。"
    )


def build_user_prompt(
    topic: str,
    num_slides: int,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
) -> str:
    """Build the user prompt with concise scenario and language guidance."""
    scenario_hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["general"])
    language_hint = LANGUAGE_HINTS.get(output_language, LANGUAGE_HINTS["zh"])
    topic_display = topic.strip() if topic.strip() else "请根据参考材料自动提炼核心主题"
    prompt = (
        f"主题：{topic_display}\n"
        f"页数：{num_slides}\n"
        f"场景：{scenario}\n"
        f"场景说明：{scenario_hint}\n"
        f"语言要求：{language_hint}\n"
    )

    if reference_text:
        reference_excerpt = reference_text[:REFERENCE_TEXT_PROMPT_LIMIT].strip()
        prompt += (
            "教学扩展模式的参考材料使用规则：\n"
            "1. 参考材料提供事实基础和重点，不要照抄整段文字。\n"
            "2. 可以补充一般性的教学背景、例子、提问和过渡，但不得与材料中的事实矛盾。\n"
            "3. 不得捏造具体数字、日期、人名、机构、研究结论或出处。\n"
            "4. 如果材料与主题不完全一致，以用户主题为主线组织内容，并保留材料中相关的事实。\n"
            f"参考材料：\n{reference_excerpt}\n"
        )

    prompt += "请直接输出最终JSON。"
    return prompt


def build_article_system_prompt(scenario: str, output_language: str) -> str:
    """System prompt for the draft-article step (plain prose, not JSON)."""
    scenario_hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["general"])
    language_hint = LANGUAGE_HINTS.get(output_language, LANGUAGE_HINTS["zh"])
    return (
        "你是巴适PPT的内容助手，负责在生成PPT大纲之前，先撰写一篇简洁、结构清晰的参考文章/讲稿草稿。\n"
        "要求：\n"
        "1. 输出纯文本文章，可用简单的小标题和段落，不要输出JSON、不要输出PPT大纲格式。\n"
        "2. 结构清楚：有引入、主体若干要点、结尾小结，便于后续转成演示文稿。\n"
        "3. 篇幅适中（约300-600字），语言自然，重点突出，不要冗长堆砌。\n"
        f"4. 场景：{scenario_hint}\n"
        f"5. 语言：{language_hint}\n"
    )


def build_article_user_prompt(
    topic: str,
    reference_text: str | None = None,
    prior_article: str | None = None,
    correction: str | None = None,
) -> str:
    """User prompt for the article step, covering topic-only / reference-only / both,
    plus an optional refinement round (prior article + a correction instruction)."""
    topic_clean = topic.strip()
    reference_excerpt = (reference_text or "").strip()[:REFERENCE_TEXT_PROMPT_LIMIT]

    parts: list[str] = []
    if topic_clean and reference_excerpt:
        parts.append(f"主题（主导方向）：{topic_clean}")
        parts.append(
            "参考材料（用于约束事实与内容，不要照抄整段，以主题为准组织）：\n" + reference_excerpt
        )
    elif reference_excerpt:
        parts.append(
            "请根据以下参考材料，提炼并组织成一篇结构清晰的文章。"
            "只整理材料中已有的信息，不要编造材料中没有的内容：\n" + reference_excerpt
        )
    else:
        parts.append(f"主题：{topic_clean or '请根据上下文自拟一个合适的主题'}")

    if prior_article and correction:
        parts.append("这是上一版草稿：\n" + prior_article.strip())
        parts.append("请根据以下修改要求重新撰写文章：\n" + correction.strip())

    parts.append("请直接输出文章正文。")
    return "\n\n".join(parts)


def build_article_messages(
    topic: str,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
    prior_article: str | None = None,
    correction: str | None = None,
) -> list[dict[str, str]]:
    """Chat messages for the draft-article step."""
    return [
        {"role": "system", "content": build_article_system_prompt(scenario, output_language)},
        {
            "role": "user",
            "content": build_article_user_prompt(
                topic=topic,
                reference_text=reference_text,
                prior_article=prior_article,
                correction=correction,
            ),
        },
    ]


NOTE_STYLE_HINTS = {
    "classroom": "课堂讲解：面向学生，循序渐进，可加入提问、举例和过渡语。",
    "sundayschool": "主日学／教会分享：语气温和，贴近信仰语境，鼓励思考与回应。",
    "parents": "家长沟通：平实诚恳，强调方法与价值，便于家长理解和配合。",
    "formal": "正式演讲：条理清晰、专业稳重，适合正式场合。",
}


def _notes_grounding_rules(mode: GenerationMode) -> str:
    if mode == "grounded":
        return (
            "9. 严格材料模式：讲稿只能依据下方【编号事实】与大纲，"
            "不得引入事实表之外的新事实、数据或出处。\n"
            "10. 每页只能展开该页标注的【事实编号】；不要把其它页面的事实挪到本页。\n"
        )
    return (
        "9. 教学创作模式：讲稿可补充举例、提问、应用等教学内容，"
        "但不得与下方【编号事实】矛盾，也不要编造具体数据或出处。\n"
    )


def build_notes_system_prompt(
    output_language: str,
    style: str,
    mode: GenerationMode = "creative",
) -> str:
    """System prompt for speaker-notes (讲稿) generation."""
    language_hint = LANGUAGE_HINTS.get(output_language, LANGUAGE_HINTS["zh"])
    style_hint = NOTE_STYLE_HINTS.get(style, NOTE_STYLE_HINTS["formal"])
    base = (
        "你是巴适PPT的备课助手，为每一页幻灯片撰写口语化的讲稿（speaker notes）。\n"
        "严格要求：\n"
        '1. 只输出合法JSON，格式为 {"notes":["第1页讲稿","第2页讲稿", ...]}，不要Markdown、不要解释。\n'
        "2. notes 数组长度必须与幻灯片页数完全一致，按页顺序一一对应。\n"
        "3. 每段讲稿是可以照着讲出来的连贯口语稿，不是要点罗列。\n"
        f"4. 讲稿风格：{style_hint}\n"
        f"5. 语言：{language_hint}\n"
        "6. 每页讲稿控制在约 80–160 字的口语要点稿（标题页和总结页更短），不要逐字写满整段时间。\n"
        "7. 讲课时长用于指导内容的深度与节奏：时间越长，每页讲得越充实、举例和过渡越多，"
        "但仍保持精炼，留给讲者临场展开，不要为凑时长而啰嗦。\n"
        "8. 以大纲为准；参考文章仅作背景，如与大纲冲突，一律以大纲为准。\n"
    )
    if mode == "grounded":
        base += _notes_grounding_rules(mode)
    return base


def build_notes_user_prompt(
    outline: dict,
    duration_minutes: int,
    article: str | None = None,
    fact_table: list[dict] | None = None,
    mode: GenerationMode = "creative",
) -> str:
    """User prompt listing the slides (and optional source article) for notes generation."""
    slides = outline.get("slides", []) if isinstance(outline, dict) else []
    n = len(slides)
    parts: list[str] = [
        f"幻灯片共 {n} 页，目标讲课总时长约 {duration_minutes} 分钟"
        "（时长仅用于把握每页的深度与节奏，不必逐字写满）。请为每一页撰写讲稿。"
    ]
    facts = _format_fact_table(fact_table) if mode == "grounded" else ""
    if facts:
        label = "唯一事实来源" if mode == "grounded" else "事实依据"
        parts.append(f"编号事实（{label}，讲稿须遵守系统提示中的模式规则）：\n{facts}")
    if article and article.strip():
        parts.append("参考文章（仅作背景，如与下面的大纲冲突，以大纲为准）：\n" + article.strip()[:REFERENCE_TEXT_PROMPT_LIMIT])
    parts.append("各页标题与要点：")
    for slide in slides:
        points = "；".join(slide.get("content_points", []) or [])
        fact_hint = ""
        if mode == "grounded":
            fact_ids = slide.get("fact_ids", [])
            fact_ids = fact_ids if isinstance(fact_ids, list) else []
            fact_hint = (
                "；事实编号："
                + ("、".join(str(item) for item in fact_ids) if fact_ids else "无")
            )
        parts.append(
            f"第{slide.get('page_number')}页 [{slide.get('slide_type')}] "
            f"{slide.get('title', '')}：{points}{fact_hint}"
        )
    parts.append(f'请直接输出 JSON：{{"notes":[...]}}（数组长度必须为 {n}）。')
    return "\n".join(parts)


def build_notes_messages(
    outline: dict,
    output_language: str,
    duration_minutes: int,
    style: str,
    article: str | None = None,
    mode: GenerationMode = "creative",
    fact_table: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Chat messages for speaker-notes generation."""
    return [
        {
            "role": "system",
            "content": build_notes_system_prompt(output_language, style, mode=mode),
        },
        {
            "role": "user",
            "content": build_notes_user_prompt(
                outline, duration_minutes, article, fact_table=fact_table, mode=mode
            ),
        },
    ]


# =====================================================================
# Grounded prompt family (fact pipeline)
# =====================================================================


def build_fact_extraction_messages(material: str) -> list[dict[str, str]]:
    """Extract facts while preserving the source material's own language."""
    system = (
        "你是多语言事实抽取助手。从给定材料中抽取关键、可直接陈述的事实，逐条编号。\n"
        "严格要求：\n"
        '1. 只输出合法JSON：{"facts":[{"id":1,"text":"..."}]}，不要解释。\n'
        "2. 每条只包含材料中明确存在的信息，不要推断、不要补充常识或材料外内容。\n"
        "3. 保留原材料使用的语言，不要翻译；中英混合术语也保持原样。\n"
        "4. 每条简短、独立、可单独引用；按出现顺序编号，从1开始。\n"
    )
    user = "材料：\n" + (material or "")[:REFERENCE_TEXT_PROMPT_LIMIT].strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _format_fact_table(fact_table: list[dict] | None) -> str:
    lines = []
    for fact in fact_table or []:
        text = str(fact.get("text", "")).strip()
        if text:
            lines.append(f"[{fact.get('id')}] {text}")
    return "\n".join(lines)


def _grounding_rules(mode: GenerationMode) -> str:
    """Extra system rules appended for strict grounded generation."""
    return (
        "\n严格材料模式(grounded)：\n"
        "G1. 下方【编号事实】是唯一允许使用的事实来源。\n"
        "G2. 每条content_points都必须由一个或多个编号事实直接支持："
        "可改写、合并、概括，但严禁加入事实表之外的背景、例子、原因、"
        "评价、建议、口号、数据、人名、出处或合理推断。\n"
        'G3. 每页新增字段 "fact_ids":[整数,...]，列出该页覆盖的事实编号；'
        "无对应事实的页用空数组 []。\n"
        "G4. 所有编号事实都必须至少表达一次。不得改变数字、时间、否定词、"
        "义务词或责任主体。\n"
        "G5. 内容页允许只有1—2个真实要点；不要为了凑数量发明第三条。\n"
        "G6. 严格模式不要生成diagram字段，用户可以在确认事实后自行添加图示。\n"
        "\n计数：必须严格输出用户指定的页数，多一页或少一页都算错误。"
    )


def _build_improved_user_prompt(
    topic: str,
    num_slides: int,
    scenario: str,
    output_language: str,
    reference_text: str | None,
    fact_table: list[dict] | None,
    mode: GenerationMode,
) -> str:
    scenario_hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["general"])
    language_hint = LANGUAGE_HINTS.get(output_language, LANGUAGE_HINTS["zh"])
    topic_display = topic.strip() if topic.strip() else "请根据参考材料/事实自动提炼核心主题"

    parts = [
        f"主题：{topic_display}",
        f"必须恰好输出 {num_slides} 页（含首页 title 与末页 conclusion），不多不少。",
        f"场景：{scenario}　场景说明：{scenario_hint}",
        f"语言要求：{language_hint}",
    ]
    facts = _format_fact_table(fact_table)
    if facts:
        parts.append(f"编号事实（唯一事实来源，按系统提示中的规则使用）：\n{facts}")
    elif reference_text:
        parts.append("参考材料：\n" + reference_text[:REFERENCE_TEXT_PROMPT_LIMIT].strip())

    parts.append(f"再次强调：必须恰好 {num_slides} 页；只输出合法 JSON。请直接输出最终 JSON。")
    return "\n".join(parts)


def build_messages(
    topic: str,
    num_slides: int,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
    mode: GenerationMode = "creative",
    fact_table: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Return product prompt messages for creative or grounded generation."""
    if mode == "creative":
        return [
            {
                "role": "system",
                "content": build_system_prompt("creative", output_language),
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    topic=topic,
                    num_slides=num_slides,
                    scenario=scenario,
                    output_language=output_language,
                    reference_text=reference_text,
                ),
            },
        ]

    return [
        {
            "role": "system",
            "content": build_system_prompt(mode, output_language) + _grounding_rules(mode),
        },
        {
            "role": "user",
            "content": _build_improved_user_prompt(
                topic=topic,
                num_slides=num_slides,
                scenario=scenario,
                output_language=output_language,
                reference_text=reference_text,
                fact_table=fact_table,
                mode=mode,
            ),
        },
    ]


def build_legacy_experiment_messages(
    topic: str,
    num_slides: int,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
) -> list[dict[str, str]]:
    """Historical-style experiment control; intentionally outside product modes."""
    scenario_hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["general"])
    language_hint = LANGUAGE_HINTS.get(output_language, LANGUAGE_HINTS["zh"])
    topic_display = topic.strip() if topic.strip() else "请根据参考材料自动提炼核心主题"
    user_prompt = (
        f"主题：{topic_display}\n"
        f"页数：{num_slides}\n"
        f"场景：{scenario}\n"
        f"场景说明：{scenario_hint}\n"
        f"语言要求：{language_hint}\n"
    )
    if reference_text:
        user_prompt += (
            "参考材料使用规则：\n"
            "1. 参考材料只用于提炼事实、结构和重点，不要照抄整段文字。\n"
            "2. 不要编造参考材料中没有的信息。\n"
            "3. 如果参考材料与主题不完全一致，以主题和场景为准，合理整理内容。\n"
            f"参考材料：\n{reference_text[:REFERENCE_TEXT_PROMPT_LIMIT].strip()}\n"
        )
    user_prompt += "请直接输出最终JSON。"
    return [
        {
            "role": "system",
            "content": build_system_prompt("creative", output_language),
        },
        {"role": "user", "content": user_prompt},
    ]


def build_grounded_repair_messages(
    *,
    previous_outline: dict,
    target_slides: int,
    output_language: str,
    fact_table: list[dict],
    missing_fact_ids: list[int] | None = None,
) -> list[dict[str, str]]:
    """Repair one grounded outline without discarding its existing structure."""
    previous_slides = previous_outline.get("slides", [])
    actual_slides = len(previous_slides) if isinstance(previous_slides, list) else 0
    if actual_slides > target_slides:
        direction = (
            f"当前多出 {actual_slides - target_slides} 页。请合并主题相近的内容页，"
            "绝不能删除任何事实。"
        )
    else:
        direction = (
            f"当前少了 {target_slides - actual_slides} 页。请拆分信息较密集的内容页，"
            "绝不能增加事实表之外的内容。"
        )
    missing_hint = ""
    if missing_fact_ids:
        missing_hint = (
            "\n上一版尚未声明覆盖这些事实编号："
            + "、".join(str(item) for item in missing_fact_ids)
            + "。修复版必须覆盖它们。"
        )

    user_prompt = (
        f"目标：把下面这份 {actual_slides} 页大纲修复为恰好 {target_slides} 页。"
        "不要另起炉灶重写主题。\n"
        f"{direction}\n"
        "所有确认事实都必须至少由一页的 fact_ids 引用；"
        "每页 fact_ids 只能填写该页文字实际表达的事实编号。"
        f"{missing_hint}\n"
        "确认事实表：\n"
        f"{_format_fact_table(fact_table)}\n"
        "上一版大纲：\n"
        f"{json.dumps(previous_outline, ensure_ascii=False)}\n"
        f"再次强调：必须恰好 {target_slides} 页，只输出修复后的合法 JSON。"
    )
    return [
        {
            "role": "system",
            "content": (
                build_system_prompt("grounded", output_language)
                + _grounding_rules("grounded")
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
