"""
Prompt templates for outline generation.

Design goals:
- Keep the system prompt compact for local 4B models
- Generate prompt rules directly from schema.py constraints
- Force JSON-only output and forbid chart/image metadata
- Allow optional pasted reference text without bloating the prompt too far
"""

from schema import OUTLINE_CONSTRAINTS, SLIDE_CONSTRAINTS

SCENARIO_HINTS = {
    "teaching": "面向课堂教学，语言清楚、适合学生理解。",
    "church": "面向教会讲座或主日学，语气温和、内容尊重信仰语境。",
    "parents": "面向家长说明会，强调价值、方法与沟通。",
    "general": "面向通用演示，结构清楚、表达自然。",
}

LANGUAGE_HINTS = {
    "zh": "全部内容使用简体中文。",
    "en": "All content must be in natural English.",
    "bilingual": "标题和要点尽量中英双语并保持简洁。",
}

REFERENCE_TEXT_PROMPT_LIMIT = 5000


def build_system_prompt() -> str:
    """Build the compact system prompt from shared schema constraints."""
    title_constraints = SLIDE_CONSTRAINTS["title"]
    content_constraints = SLIDE_CONSTRAINTS["content"]
    conclusion_constraints = SLIDE_CONSTRAINTS["conclusion"]

    return (
        "你是巴适PPT的大纲生成助手。根据用户主题生成演示文稿大纲。\n"
        "严格要求：\n"
        "1. 只输出合法JSON，不要Markdown，不要解释。\n"
        "2. 顶层格式必须是 "
        '{"title":"演示标题","slides":[{"page_number":1,"title":"页面标题","content_points":["要点1","要点2"],"slide_type":"title"}]}。\n'
        "其中 content_points 必须是包含多个独立字符串的 JSON 数组，绝对不能合并为一个带换行符的单字符串。\n"
        f"3. 总页数必须在{OUTLINE_CONSTRAINTS['min_slides']}-{OUTLINE_CONSTRAINTS['max_slides']}之间。\n"
        "4. 结构必须是：第一页title，中间全部是content，最后一页conclusion。\n"
        f"5. 标题页：{title_constraints['min_points']}-{title_constraints['max_points']}个要点，每点不超过"
        f"{title_constraints['max_point_length']}字，页标题不超过{title_constraints['max_title_length']}字。\n"
        f"6. 内容页：{content_constraints['min_points']}-{content_constraints['max_points']}个要点，每点不超过"
        f"{content_constraints['max_point_length']}字，页标题不超过{content_constraints['max_title_length']}字。\n"
        f"7. 总结页：{conclusion_constraints['min_points']}-{conclusion_constraints['max_points']}个要点，每点不超过"
        f"{conclusion_constraints['max_point_length']}字，页标题不超过{conclusion_constraints['max_title_length']}字。\n"
        "8. page_number 必须从1开始连续编号。\n"
        "9. 不要生成chart_config、image_config、description或type字段。\n"
        "10. 仅在内容页（content），当某页适合用流程图、关系图或步骤图来解释时，"
        "可以可选地添加一个 diagram 字段，值为合法的 Mermaid 代码"
        '（例如 "flowchart LR; A[输入]-->B[处理]-->C[输出]"）。'
        "节点文字要简短。若该页不需要图示，则省略 diagram 字段。标题页和总结页不要加 diagram。\n"
        "11. 内容要贴合主题，顺序自然，适合目标受众。"
    )


def build_user_prompt(
    topic: str,
    num_slides: int,
    scenario: str,
    language: str,
    reference_text: str | None = None,
) -> str:
    """Build the user prompt with concise scenario and language guidance."""
    scenario_hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["general"])
    language_hint = LANGUAGE_HINTS.get(language, LANGUAGE_HINTS["zh"])
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
            "参考材料使用规则：\n"
            "1. 参考材料只用于提炼事实、结构和重点，不要照抄整段文字。\n"
            "2. 不要编造参考材料中没有的信息。\n"
            "3. 如果参考材料与主题不完全一致，以主题和场景为准，合理整理内容。\n"
            f"参考材料：\n{reference_excerpt}\n"
        )

    prompt += "请直接输出最终JSON。"
    return prompt


def build_messages(
    topic: str,
    num_slides: int,
    scenario: str,
    language: str,
    reference_text: str | None = None,
) -> list[dict[str, str]]:
    """Return OpenAI-style chat messages for outline generation."""
    return [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_prompt(
                topic=topic,
                num_slides=num_slides,
                scenario=scenario,
                language=language,
                reference_text=reference_text,
            ),
        },
    ]
