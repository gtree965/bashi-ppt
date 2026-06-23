"""Rigorous prompt/grounding experiment using the original failure cases.

The experiment deliberately separates:

1. generation from a human-authored gold fact table;
2. model-based fact extraction from raw material;
3. prompt family (legacy vs grounded);
4. sampling temperature (0.7 vs 0.2);
5. model and inference-mode choice, with provider metadata recorded.

Raw model output is scored before any production parser repair or slide-count
reconciliation. Every request, response, fact table, and machine score is
persisted for later human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
REPO_ROOT = BACKEND.parent
QUALITY = REPO_ROOT / "docs" / "quality"
CASES_PATH = QUALITY / "model-qualification" / "cases.json"
GOLD_PATH = QUALITY / "prompt-experiment" / "gold-facts-v2.json"
OUTPUT_BASE = QUALITY / "prompt-experiment" / "results-v2"

for path in (BACKEND,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from llm.prompts import (  # noqa: E402
    build_fact_extraction_messages,
    build_legacy_experiment_messages,
    build_messages,
    build_notes_messages,
)


load_dotenv(REPO_ROOT / ".env", override=False)


MODELS = {
    "qwen": {
        "label": "SiliconFlow Qwen3.6-35B-A3B",
        "model": "Qwen/Qwen3.6-35B-A3B",
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "siliconflow_API_KEY",
        "extra_body": {"enable_thinking": False},
    },
    "deepseek-flash": {
        "label": "SiliconFlow DeepSeek-V4-Flash",
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "siliconflow_API_KEY",
        "extra_body": {"enable_thinking": False},
    },
    "deepseek-pro": {
        "label": "SiliconFlow DeepSeek-V4-Pro",
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "provider": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "siliconflow_API_KEY",
        "extra_body": {"enable_thinking": False},
    },
    "dashscope-qwen37-off": {
        "label": "DashScope Beijing Qwen3.7 Plus (thinking off)",
        "model": "qwen3.7-plus",
        "provider": "DashScope Beijing",
        "base_url": (
            "https://ws-smkrwadfehthfwgd.cn-beijing.maas.aliyuncs.com/"
            "compatible-mode/v1"
        ),
        "api_key_env": "DASHSCOPE_API_KEY",
        "extra_body": {"enable_thinking": False},
    },
    "dashscope-qwen37-on": {
        "label": "DashScope Beijing Qwen3.7 Plus (thinking on)",
        "model": "qwen3.7-plus",
        "provider": "DashScope Beijing",
        "base_url": (
            "https://ws-smkrwadfehthfwgd.cn-beijing.maas.aliyuncs.com/"
            "compatible-mode/v1"
        ),
        "api_key_env": "DASHSCOPE_API_KEY",
        "extra_body": {"enable_thinking": True},
    },
}


@dataclass
class MachineScore:
    parsed: bool
    raw_count: int
    count_ok: bool
    structure_ok: bool
    point_constraints_ok: bool
    point_constraint_violations: list[str]
    observed_fact_ids: list[int]
    missing_fact_ids: list[int]
    critical_missing_ids: list[int]
    fact_coverage: float
    critical_coverage: float
    forbidden_hits: list[str]
    new_numbers: list[str]
    declared_fact_ids: list[int]
    invalid_declared_ids: list[int]
    unsupported_declared_ids: list[int]
    unmatched_grounded_points: list[str]
    fidelity_pass: bool
    layout_pass: bool
    content_pass: bool
    grounding_audit_pass: bool
    quality_pass: bool


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strip_fences(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s*```\s*$", "", text).strip()


def parse_lenient(raw: str) -> Any:
    text = strip_fences(raw)
    try:
        return json.loads(text)
    except Exception:
        try:
            from json_repair import repair_json

            return json.loads(repair_json(text))
        except Exception:
            return None


def output_blob(parsed: Any, workflow: str) -> tuple[str, list[dict], list[str]]:
    if workflow == "outline":
        slides = parsed.get("slides", []) if isinstance(parsed, dict) else []
        slides = [slide for slide in slides if isinstance(slide, dict)]
        parts: list[str] = []
        for slide in slides:
            parts.append(str(slide.get("title", "")))
            points = slide.get("content_points", [])
            if isinstance(points, list):
                parts.extend(str(point) for point in points)
            elif points:
                parts.append(str(points))
        return "\n".join(parts), slides, []

    notes = parsed.get("notes", []) if isinstance(parsed, dict) else []
    notes = [str(note) for note in notes] if isinstance(notes, list) else []
    return "\n".join(notes), [], notes


def fact_matches(text: str, fact: dict[str, Any]) -> bool:
    return all(re.search(pattern, text, flags=re.IGNORECASE) for pattern in fact["match_all"])


def fact_partially_matches(text: str, fact: dict[str, Any]) -> bool:
    """Whether a short bullet is traceable to at least one component of a fact.

    Full fact coverage remains conjunctive. This looser check is only used to
    flag obviously free-floating bullets because one compound fact is often
    split across several concise slide bullets.
    """
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in fact["match_all"])


def source_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?::\d+)?%?", text))


def output_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?::\d+)?%?", text))


def declared_ids(slides: list[dict]) -> list[int]:
    found: list[int] = []
    for slide in slides:
        values = slide.get("fact_ids", [])
        if not isinstance(values, list):
            continue
        found.extend(value for value in values if isinstance(value, int))
    return sorted(set(found))


def score_output(
    raw: str,
    *,
    workflow: str,
    expected_count: int,
    material: str,
    gold: dict[str, Any],
    grounded: bool,
) -> MachineScore:
    parsed = parse_lenient(raw)
    blob, slides, notes = output_blob(parsed, workflow)
    raw_count = len(slides) if workflow == "outline" else len(notes)
    count_ok = raw_count == expected_count
    structure_ok = True
    point_constraints_ok = True
    point_constraint_violations: list[str] = []
    if workflow == "outline":
        structure_ok = bool(slides)
        if slides:
            structure_ok = (
                slides[0].get("slide_type") == "title"
                and slides[-1].get("slide_type") == "conclusion"
                and all(
                    slide.get("slide_type") == "content"
                    for slide in slides[1:-1]
                )
            )
        limits = {
            "title": (2, 4),
            "content": (3, 5),
            "conclusion": (2, 4),
        }
        for index, slide in enumerate(slides, start=1):
            slide_type = slide.get("slide_type")
            minimum, maximum = limits.get(slide_type, (1, 5))
            points = slide.get("content_points", [])
            count = len(points) if isinstance(points, list) else 0
            if not minimum <= count <= maximum:
                point_constraint_violations.append(
                    f"slide {index} ({slide_type}) has {count} points; "
                    f"expected {minimum}-{maximum}"
                )
        point_constraints_ok = not point_constraint_violations

    observed = [
        fact["id"]
        for fact in gold["facts"]
        if fact_matches(blob, fact)
    ]
    required_ids = [fact["id"] for fact in gold["facts"]]
    critical_ids = [
        fact["id"]
        for fact in gold["facts"]
        if fact.get("critical")
    ]
    missing = sorted(set(required_ids) - set(observed))
    critical_missing = sorted(set(critical_ids) - set(observed))
    fact_coverage = round(len(observed) / max(len(required_ids), 1), 3)
    critical_coverage = round(
        (len(critical_ids) - len(critical_missing)) / max(len(critical_ids), 1),
        3,
    )
    forbidden_hits = [
        item["label"]
        for item in gold.get("forbidden", [])
        if re.search(item["pattern"], blob, flags=re.IGNORECASE)
    ]
    new_numbers = sorted(output_numbers(blob) - source_numbers(material))

    declared = declared_ids(slides) if grounded and workflow == "outline" else []
    invalid_declared = sorted(set(declared) - set(required_ids))
    unsupported_declared: list[int] = []
    unmatched_grounded_points: list[str] = []
    if grounded and workflow == "outline":
        for slide in slides:
            slide_text, _, _ = output_blob({"slides": [slide]}, "outline")
            values = slide.get("fact_ids", [])
            if not isinstance(values, list):
                continue
            for value in values:
                fact = next(
                    (item for item in gold["facts"] if item["id"] == value),
                    None,
                )
                if fact is not None and not fact_matches(slide_text, fact):
                    unsupported_declared.append(value)
            points = slide.get("content_points", [])
            if isinstance(points, list):
                for point in points:
                    point_text = str(point)
                    if not any(
                        fact_partially_matches(point_text, fact)
                        for fact in gold["facts"]
                    ):
                        unmatched_grounded_points.append(point_text)
        unsupported_declared = sorted(set(unsupported_declared))

    grounding_audit_pass = (
        not grounded
        or workflow != "outline"
        or (
            bool(declared)
            and not invalid_declared
            and not unsupported_declared
            and not unmatched_grounded_points
        )
    )
    fidelity_pass = (
        parsed is not None
        and count_ok
        and structure_ok
        and critical_coverage == 1.0
        and fact_coverage >= float(gold["minimum_coverage"])
        and not forbidden_hits
        and not new_numbers
    )
    layout_pass = point_constraints_ok
    content_pass = fidelity_pass
    quality_pass = fidelity_pass and layout_pass and grounding_audit_pass
    return MachineScore(
        parsed=parsed is not None,
        raw_count=raw_count,
        count_ok=count_ok,
        structure_ok=structure_ok,
        point_constraints_ok=point_constraints_ok,
        point_constraint_violations=point_constraint_violations,
        observed_fact_ids=observed,
        missing_fact_ids=missing,
        critical_missing_ids=critical_missing,
        fact_coverage=fact_coverage,
        critical_coverage=critical_coverage,
        forbidden_hits=forbidden_hits,
        new_numbers=new_numbers,
        declared_fact_ids=declared,
        invalid_declared_ids=invalid_declared,
        unsupported_declared_ids=unsupported_declared,
        unmatched_grounded_points=unmatched_grounded_points,
        fidelity_pass=fidelity_pass,
        layout_pass=layout_pass,
        content_pass=content_pass,
        grounding_audit_pass=grounding_audit_pass,
        quality_pass=quality_pass,
    )


def request_messages(
    case: dict[str, Any],
    workflow: str,
    mode: str,
    facts: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    if mode == "grounded":
        return grounded_v2_messages(case, workflow, facts or [])
    if workflow == "outline":
        return build_legacy_experiment_messages(
            topic=case["topic"],
            num_slides=case["num_slides"],
            scenario=case["scenario"],
            output_language=case["language"],
            reference_text=case["reference_text"],
        )
    return build_notes_messages(
        outline=case["notes_outline"],
        output_language=case["language"],
        duration_minutes=case["notes_duration"],
        style=case["notes_style"],
        article=case["reference_text"],
        mode="creative",
    )


def format_facts(facts: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{fact['id']}] {fact['text']}" for fact in facts)


def grounded_v2_messages(
    case: dict[str, Any],
    workflow: str,
    facts: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Closed-book experimental prompt with auditable grounding rules."""
    fact_text = format_facts(facts)
    if workflow == "outline":
        system = (
            "你是巴适PPT的严格材料整理器，不是自由创作助手。"
            "【编号事实】是唯一事实来源。\n"
            "必须遵守：\n"
            "1. 只输出合法JSON，不要Markdown或解释。\n"
            "2. 顶层格式为"
            '{"title":"标题","slides":[{"page_number":1,"title":"页标题",'
            '"content_points":["要点"],"slide_type":"title","fact_ids":[1]}]}。\n'
            f"3. 必须恰好输出{case['num_slides']}页，不多不少；第一页title，"
            "最后一页conclusion，中间全部content，页码从1连续编号。\n"
            "4. 标题页2—4个要点；内容页3—5个要点；总结页2—4个要点。\n"
            "5. 每条要点都必须能由一个或多个编号事实直接支持。"
            "不得加入材料外背景、例子、原因、评价、建议、口号或合理推断。\n"
            "6. 每页fact_ids只能列出该页文字实际表达的事实编号；"
            "不得把未表达的编号挂在页面上，也不得把全部编号堆到总结页。\n"
            "7. 所有编号事实都必须至少在一页中得到表达；"
            "可合并和改写，但不得遗漏、改变数字时间、弱化否定词或改变责任主体。\n"
            "8. 不要输出diagram、description、image_config或其他字段。\n"
        )
        user = (
            f"主题：{case['topic'] or '根据材料提炼'}\n"
            f"场景：{case['scenario']}\n"
            f"语言：{case['language']}\n"
            f"必须恰好{case['num_slides']}页。\n"
            f"【编号事实】\n{fact_text}\n"
            "提交前自行检查：页数准确；每个事实至少使用一次；"
            "每个fact_id与本页文字一致；没有事实表外内容。现在只输出最终JSON。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    outline = case["notes_outline"]
    slide_lines = []
    for slide in outline["slides"]:
        points = "；".join(slide.get("content_points", []))
        slide_lines.append(
            f"第{slide['page_number']}页 {slide['title']}：{points}"
        )
    count = len(outline["slides"])
    system = (
        "你是巴适PPT的严格材料讲稿整理器，不是自由创作助手。"
        "【编号事实】和给定大纲是唯一内容来源。\n"
        "必须遵守：\n"
        '1. 只输出合法JSON：{"notes":["第1页讲稿", "..."]}。\n'
        f"2. notes必须恰好{count}段，与幻灯片逐页一一对应。\n"
        "3. 可使用自然过渡语和面向儿童/学生的简单提问，"
        "但不得加入新的事实、背景、故事细节、数据、出处、教义或历史解释。\n"
        "4. 不得改变任何数字、时间、否定词、报名规则或责任主体。\n"
        "5. 每段只讲对应页面已有要点；不为凑字数扩写。\n"
    )
    user = (
        f"语言：{case['language']}；风格：{case['notes_style']}；"
        f"目标时长：{case['notes_duration']}分钟。\n"
        f"【编号事实】\n{fact_text}\n"
        "【各页大纲】\n"
        + "\n".join(slide_lines)
        + f"\n再次确认：只输出JSON，notes数组必须恰好{count}段。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_request_payload(
    *,
    spec: dict[str, Any],
    messages: list[dict[str, str]],
    temperature: float,
) -> dict[str, Any]:
    payload = {
        "model": spec["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    payload.update(spec.get("extra_body", {}))
    return payload


def call_provider(
    client: httpx.Client,
    *,
    spec: dict[str, Any],
    messages: list[dict[str, str]],
    temperature: float,
    timeout: float,
    max_attempts: int,
) -> tuple[str, dict[str, Any], float, int]:
    payload = build_request_payload(
        spec=spec,
        messages=messages,
        temperature=temperature,
    )
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        try:
            response = client.post(
                f"{spec['base_url'].rstrip('/')}/chat/completions",
                json=payload,
                timeout=timeout,
            )
        except httpx.RequestError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_attempts:
                time.sleep(min(2**attempt, 10))
                continue
            raise RuntimeError(last_error) from exc
        elapsed = time.perf_counter() - started
        if response.is_success:
            data = response.json()
            choices = data.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
            if content.strip():
                return content.strip(), data, elapsed, attempt
            last_error = f"HTTP 200 without usable content: {response.text[:500]}"
        else:
            last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                break
        if attempt < max_attempts:
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(last_error)


def response_metrics(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    reasoning = message.get("reasoning_content") or ""
    usage = response.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "reasoning_chars": len(reasoning),
        "finish_reason": choices[0].get("finish_reason") if choices else None,
    }


def selected_cases() -> tuple[dict[str, dict], dict[str, dict]]:
    cases = {
        item["id"]: item
        for item in read_json(CASES_PATH)["cases"]
        if item["id"] in {
            "reference_only_facts",
            "long_material_compression",
            "church_good_samaritan",
        }
    }
    gold = {
        item["case_id"]: item
        for item in read_json(GOLD_PATH)["cases"]
    }
    return cases, gold


def run_generation(args: argparse.Namespace, root: Path) -> list[dict[str, Any]]:
    cases, gold_by_case = selected_cases()
    tasks = [
        ("reference_only_facts", "outline"),
        ("reference_only_facts", "notes"),
        ("long_material_compression", "outline"),
        ("church_good_samaritan", "outline"),
        ("church_good_samaritan", "notes"),
    ]
    cells = [
        ("legacy", 0.7),
        ("legacy", 0.2),
        ("grounded", 0.7),
        ("grounded", 0.2),
    ]
    if args.focused:
        cells = [("grounded", 0.2)]
    if args.smoke:
        tasks = tasks[:1]
        cells = [("legacy", 0.2), ("grounded", 0.2)]

    rows: list[dict[str, Any]] = []
    for model_key in args.models:
        spec = MODELS[model_key]
        key = os.getenv(spec["api_key_env"], "")
        if not key:
            raise RuntimeError(f"{spec['api_key_env']} is missing")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(headers=headers, verify=False) as http:
            for case_id, workflow in tasks:
                case = cases[case_id]
                gold = gold_by_case[case_id]
                facts = [
                    {"id": item["id"], "text": item["text"]}
                    for item in gold["facts"]
                ]
                for mode, temperature in cells:
                    for repetition in range(1, args.reps + 1):
                        messages = request_messages(
                            case,
                            workflow,
                            mode,
                            facts if mode == "grounded" else None,
                        )
                        stem = (
                            root
                            / "generation"
                            / model_key
                            / case_id
                            / workflow
                            / f"{mode}-t{temperature}-r{repetition}"
                        )
                        write_json(stem / "request-messages.json", messages)
                        write_json(stem / "gold-facts.json", facts)
                        started = time.perf_counter()
                        try:
                            raw, response, elapsed, attempts = call_provider(
                                http,
                                spec=spec,
                                messages=messages,
                                temperature=temperature,
                                timeout=args.timeout,
                                max_attempts=args.max_attempts,
                            )
                            write_text(stem / "raw.txt", raw)
                            write_json(stem / "response.json", response)
                            score = score_output(
                                raw,
                                workflow=workflow,
                                expected_count=(
                                    case["num_slides"]
                                    if workflow == "outline"
                                    else len(case["notes_outline"]["slides"])
                                ),
                                material=case["reference_text"],
                                gold=gold,
                                grounded=mode == "grounded",
                            )
                            write_json(stem / "score.json", asdict(score))
                            row = {
                                "phase": "generation",
                                "model_key": model_key,
                                "model": spec["model"],
                                "model_label": spec["label"],
                                "provider": spec["provider"],
                                "thinking_enabled": bool(
                                    spec.get("extra_body", {}).get(
                                        "enable_thinking",
                                        False,
                                    )
                                ),
                                "case_id": case_id,
                                "workflow": workflow,
                                "mode": mode,
                                "temperature": temperature,
                                "repetition": repetition,
                                "elapsed_seconds": round(elapsed, 3),
                                "runner_seconds": round(time.perf_counter() - started, 3),
                                "attempts": attempts,
                                **response_metrics(response),
                                **asdict(score),
                            }
                        except Exception as exc:
                            row = {
                                "phase": "generation",
                                "model_key": model_key,
                                "model": spec["model"],
                                "model_label": spec["label"],
                                "provider": spec["provider"],
                                "thinking_enabled": bool(
                                    spec.get("extra_body", {}).get(
                                        "enable_thinking",
                                        False,
                                    )
                                ),
                                "case_id": case_id,
                                "workflow": workflow,
                                "mode": mode,
                                "temperature": temperature,
                                "repetition": repetition,
                                "quality_pass": False,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                            write_json(stem / "error.json", row)
                        rows.append(row)
                        print(
                            f"[generation] {model_key} {case_id}/{workflow} "
                            f"{mode}@{temperature} r{repetition}: "
                            f"{'PASS' if row.get('quality_pass') else 'FAIL'}",
                            flush=True,
                        )
    return rows


def run_extraction(args: argparse.Namespace, root: Path) -> list[dict[str, Any]]:
    cases, gold_by_case = selected_cases()
    rows: list[dict[str, Any]] = []
    for model_key in args.models:
        spec = MODELS[model_key]
        key = os.getenv(spec["api_key_env"], "")
        if not key:
            raise RuntimeError(f"{spec['api_key_env']} is missing")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(headers=headers, verify=False) as http:
            for case_id, case in cases.items():
                gold = gold_by_case[case_id]
                messages = build_fact_extraction_messages(case["reference_text"])
                for repetition in range(1, args.extraction_reps + 1):
                    stem = (
                        root
                        / "extraction"
                        / model_key
                        / case_id
                        / f"r{repetition}"
                    )
                    write_json(stem / "request-messages.json", messages)
                    try:
                        raw, response, elapsed, attempts = call_provider(
                            http,
                            spec=spec,
                            messages=messages,
                            temperature=0.0,
                            timeout=args.timeout,
                            max_attempts=args.max_attempts,
                        )
                        write_text(stem / "raw.txt", raw)
                        write_json(stem / "response.json", response)
                        score = score_extraction(
                            raw,
                            material=case["reference_text"],
                            gold=gold,
                        )
                        write_json(stem / "score.json", score)
                        row = {
                            "phase": "extraction",
                            "model_key": model_key,
                            "model": spec["model"],
                            "model_label": spec["label"],
                            "provider": spec["provider"],
                            "thinking_enabled": bool(
                                spec.get("extra_body", {}).get(
                                    "enable_thinking",
                                    False,
                                )
                            ),
                            "case_id": case_id,
                            "temperature": 0.0,
                            "repetition": repetition,
                            "elapsed_seconds": round(elapsed, 3),
                            "attempts": attempts,
                            **response_metrics(response),
                            **score,
                        }
                    except Exception as exc:
                        row = {
                            "phase": "extraction",
                            "model_key": model_key,
                            "model": spec["model"],
                            "model_label": spec["label"],
                            "provider": spec["provider"],
                            "thinking_enabled": bool(
                                spec.get("extra_body", {}).get(
                                    "enable_thinking",
                                    False,
                                )
                            ),
                            "case_id": case_id,
                            "temperature": 0.0,
                            "repetition": repetition,
                            "quality_pass": False,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                        write_json(stem / "error.json", row)
                    rows.append(row)
                    print(
                        f"[extraction] {model_key} {case_id} r{repetition}: "
                        f"{'PASS' if row.get('quality_pass') else 'FAIL'}",
                        flush=True,
                    )
    return rows


def score_extraction(
    raw: str,
    *,
    material: str,
    gold: dict[str, Any],
) -> dict[str, Any]:
    parsed = parse_lenient(raw)
    extracted = parsed.get("facts", []) if isinstance(parsed, dict) else []
    extraction_blob = "\n".join(
        str(item.get("text", "")) if isinstance(item, dict) else str(item)
        for item in extracted
    )
    observed = [
        fact["id"]
        for fact in gold["facts"]
        if fact_matches(extraction_blob, fact)
    ]
    critical = [
        fact["id"]
        for fact in gold["facts"]
        if fact.get("critical")
    ]
    missing = sorted(
        {fact["id"] for fact in gold["facts"]} - set(observed)
    )
    critical_missing = sorted(set(critical) - set(observed))
    coverage = round(len(observed) / max(len(gold["facts"]), 1), 3)
    critical_coverage = round(
        (len(critical) - len(critical_missing)) / max(len(critical), 1),
        3,
    )
    forbidden_hits = [
        item["label"]
        for item in gold.get("forbidden", [])
        if re.search(item["pattern"], extraction_blob, flags=re.IGNORECASE)
    ]
    new_numbers = sorted(output_numbers(extraction_blob) - source_numbers(material))
    passed = (
        parsed is not None
        and critical_coverage == 1.0
        and coverage >= float(gold["minimum_coverage"])
        and not forbidden_hits
        and not new_numbers
    )
    return {
        "parsed": parsed is not None,
        "fact_count": len(extracted),
        "observed_fact_ids": observed,
        "missing_fact_ids": missing,
        "critical_missing_ids": critical_missing,
        "fact_coverage": coverage,
        "critical_coverage": critical_coverage,
        "forbidden_hits": forbidden_hits,
        "new_numbers": new_numbers,
        "quality_pass": passed,
    }


def rescore_existing(root: Path) -> list[dict[str, Any]]:
    cases, gold_by_case = selected_cases()
    rows = read_json(root / "metrics.json")
    rescored: list[dict[str, Any]] = []
    for row in rows:
        if row.get("error"):
            rescored.append(row)
            continue
        model_key = row["model_key"]
        case_id = row["case_id"]
        repetition = row["repetition"]
        case = cases[case_id]
        gold = gold_by_case[case_id]
        if row["phase"] == "generation":
            workflow = row["workflow"]
            mode = row["mode"]
            temperature = row["temperature"]
            stem = (
                root
                / "generation"
                / model_key
                / case_id
                / workflow
                / f"{mode}-t{temperature}-r{repetition}"
            )
            raw = (stem / "raw.txt").read_text(encoding="utf-8")
            score = score_output(
                raw,
                workflow=workflow,
                expected_count=(
                    case["num_slides"]
                    if workflow == "outline"
                    else len(case["notes_outline"]["slides"])
                ),
                material=case["reference_text"],
                gold=gold,
                grounded=mode == "grounded",
            )
            write_json(stem / "score.json", asdict(score))
            keep = {
                key: value
                for key, value in row.items()
                if key not in MachineScore.__dataclass_fields__
            }
            rescored.append({**keep, **asdict(score)})
        else:
            stem = root / "extraction" / model_key / case_id / f"r{repetition}"
            raw = (stem / "raw.txt").read_text(encoding="utf-8")
            score = score_extraction(
                raw,
                material=case["reference_text"],
                gold=gold,
            )
            write_json(stem / "score.json", score)
            score_keys = set(score)
            keep = {key: value for key, value in row.items() if key not in score_keys}
            rescored.append({**keep, **score})
    write_json(root / "metrics.json", rescored)
    markdown_summary(rescored, root)
    return rescored


def markdown_summary(rows: list[dict[str, Any]], root: Path) -> None:
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        if row["phase"] == "generation":
            key = (
                row["model_key"],
                row["case_id"],
                row["workflow"],
                row["mode"],
                row["temperature"],
            )
        else:
            key = (row["model_key"], row["case_id"], "extraction", "gold", 0.0)
        groups.setdefault(key, []).append(row)

    lines = [
        "# Grounding experiment v2 automated summary",
        "",
        "> Machine scores are screening signals, not a substitute for human review.",
        "",
        "| model | case | workflow | mode | temp | full pass | fidelity | layout | audit | mean coverage | critical | forbidden runs |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, items in sorted(groups.items()):
        model, case_id, workflow, mode, temperature = key
        passed = sum(bool(item.get("quality_pass")) for item in items)
        fidelity_passed = sum(bool(item.get("fidelity_pass")) for item in items)
        layout_passed = sum(bool(item.get("layout_pass")) for item in items)
        audit_passed = sum(bool(item.get("grounding_audit_pass")) for item in items)
        coverage_values = [
            float(item["fact_coverage"])
            for item in items
            if item.get("fact_coverage") is not None
        ]
        critical_values = [
            float(item["critical_coverage"])
            for item in items
            if item.get("critical_coverage") is not None
        ]
        mean_coverage = (
            sum(coverage_values) / len(coverage_values)
            if coverage_values
            else 0
        )
        mean_critical = (
            sum(critical_values) / len(critical_values)
            if critical_values
            else 0
        )
        forbidden_runs = sum(bool(item.get("forbidden_hits")) for item in items)
        lines.append(
            f"| {model} | {case_id} | {workflow} | {mode} | {temperature} | "
            f"{passed}/{len(items)} | {fidelity_passed}/{len(items)} | "
            f"{layout_passed}/{len(items)} | {audit_passed}/{len(items)} | "
            f"{mean_coverage:.3f} | "
            f"{mean_critical:.3f} | {forbidden_runs} |"
        )
    write_text(root / "SUMMARY.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        nargs="+",
        choices=sorted(MODELS),
        default=["qwen", "deepseek-flash"],
    )
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--extraction-reps", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--focused",
        action="store_true",
        help="Run only the production-candidate grounded@0.2 generation cell.",
    )
    parser.add_argument(
        "--phase",
        choices=["all", "generation", "extraction"],
        default="all",
    )
    parser.add_argument("--rescore-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.rescore_root:
        root = args.rescore_root.resolve()
        rows = rescore_existing(root)
        print(f"Rescored {len(rows)} rows: {root}", flush=True)
        return 0
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = OUTPUT_BASE / stamp
    root.mkdir(parents=True, exist_ok=False)
    write_json(
        root / "run-config.json",
        {
            "timestamp": stamp,
            "models": args.models,
            "reps": args.reps,
            "extraction_reps": args.extraction_reps,
            "phase": args.phase,
            "smoke": args.smoke,
            "focused": args.focused,
            "providers": {
                model_key: {
                    "provider": MODELS[model_key]["provider"],
                    "base_url": MODELS[model_key]["base_url"],
                    "model": MODELS[model_key]["model"],
                    "thinking_enabled": bool(
                        MODELS[model_key].get("extra_body", {}).get(
                            "enable_thinking",
                            False,
                        )
                    ),
                }
                for model_key in args.models
            },
            "temperature_cells": [0.7, 0.2],
            "cases_sha256": hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
            "gold_sha256": hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest(),
            "credentials_recorded": False,
        },
    )
    rows: list[dict[str, Any]] = []
    if args.phase in {"all", "generation"}:
        rows.extend(run_generation(args, root))
    if args.phase in {"all", "extraction"} and not args.smoke:
        rows.extend(run_extraction(args, root))
    write_json(root / "metrics.json", rows)
    markdown_summary(rows, root)
    print(f"Results: {root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
