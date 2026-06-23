"""2x2(xN-model) factorial experiment: prompt(legacy|improved) x temperature.

Answers the four questions from the plan:
  - how much does lowering temperature help?
  - how much does the improved prompt (mode separation + fact pipeline) help?
  - does the combination pass reliably?
  - what residual must be solved by the program (count reconcile, etc.)?

Metrics are machine-checkable:
  - count exactness on the *raw* model output (before our program reconcile),
  - grounding via per-slide fact_ids (improved arm only): no invalid ids, no
    ungrounded content slide, fact coverage,
  - a mechanism-independent fabrication proxy: numbers/years in the output that
    do NOT appear in the source material,
  - bilingual notes: array length == slide count and each note has CJK+Latin.

Usage (from backend/):
  ../venv/Scripts/python.exe -m experiments.grounding_experiment --smoke
  ../venv/Scripts/python.exe -m experiments.grounding_experiment --models siliconflow
  ../venv/Scripts/python.exe -m experiments.grounding_experiment --models siliconflow,gemma --reps 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

import config
from llm import client
from llm.outline_parser import parse_outline

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover
    repair_json = None


# --------------------------------------------------------------------------- #
# Models (config overrides). SiliconFlow key comes from .env; Gemma from LM Studio.
# --------------------------------------------------------------------------- #
MODELS = {
    "siliconflow": {
        "label": "SiliconFlow Qwen3.5-35B-A3B",
        "provider": "openrouter",  # cloud: base_url used as-is, key honoured
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": os.getenv("siliconflow_API_KEY", ""),
        "model": "Qwen/Qwen3.5-35B-A3B",
        "verify_ssl": False,
    },
    "gemma": {
        "label": "Local Gemma 4 12B QAT (LM Studio)",
        "provider": "lmstudio",
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "model": "google/gemma-4-12b-qat",
        "verify_ssl": True,
    },
}


def apply_model(spec: dict) -> None:
    config.LLM_PROVIDER = spec["provider"]
    config.LLM_BASE_URL = spec["base_url"]
    config.LLM_API_KEY = spec["api_key"]
    config.LLM_MODEL = spec["model"]
    config.VERIFY_SSL = spec["verify_ssl"]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@dataclass
class Fixture:
    name: str
    kind: str            # "outline" | "notes"
    mode: str            # improved mode used by the improved arm ("grounded")
    scenario: str
    language: str
    topic: str = ""
    material: str = ""
    expected_count: int = 5
    outline: dict | None = None   # for notes fixtures


STRICT_MATERIAL = (
    "光合作用是绿色植物利用光能，将二氧化碳和水转化为有机物并释放氧气的过程。"
    "它主要发生在叶片的叶绿体中。叶绿素是吸收光能的主要色素，呈绿色。"
    "光合作用分为光反应和暗反应两个阶段。光反应在类囊体薄膜上进行，产生ATP和NADPH。"
    "暗反应在叶绿体基质中进行，又称卡尔文循环。光合作用为地球上几乎所有生命提供能量来源。"
)

LONG_MATERIAL = (
    "宋代是中国历史上经济文化高度繁荣的时期，建立于公元960年，由赵匡胤建立。"
    "北宋的都城是东京，即今天的开封。宋代发明了活字印刷术，由毕昇在11世纪发明。"
    "指南针在宋代被广泛用于航海。火药在宋代被用于军事。宋代的科举制度更加完善，录取人数大幅增加。"
    "宋代出现了世界上最早的纸币，称为交子，最早出现在四川地区。"
    "宋代的城市商业繁荣，出现了夜市。著名画作《清明上河图》由张择端绘制，描绘了东京的市井生活。"
    "南宋的都城是临安，即今天的杭州。宋代理学兴盛，代表人物有朱熹。"
)

SUNDAYSCHOOL_MATERIAL = (
    "好撒玛利亚人的比喻记载在路加福音第十章。一个人从耶路撒冷下耶利哥，途中遭遇强盗，被打个半死。"
    "有一个祭司从那条路下来，看见他就从旁边过去了。又有一个利未人，也照样从旁边过去。"
    "惟有一个撒玛利亚人，行路来到那里，看见他就动了慈心，上前用油和酒倒在他的伤处，包裹好了，"
    "扶他骑上自己的牲口，带到店里去照应他。这个比喻教导人要爱邻舍如同自己。"
)

NOTES_OUTLINE = {
    "title": "光合作用入门",
    "slides": [
        {"page_number": 1, "slide_type": "title", "title": "光合作用入门 Photosynthesis",
         "content_points": ["什么是光合作用", "为什么重要", "学习目标"]},
        {"page_number": 2, "slide_type": "content", "title": "定义 Definition",
         "content_points": ["光能转化", "二氧化碳与水", "释放氧气"]},
        {"page_number": 3, "slide_type": "content", "title": "场所 Location",
         "content_points": ["叶绿体", "叶绿素吸光", "类囊体薄膜"]},
        {"page_number": 4, "slide_type": "content", "title": "光反应 Light Reaction",
         "content_points": ["类囊体薄膜进行", "产生ATP", "产生NADPH"]},
        {"page_number": 5, "slide_type": "content", "title": "暗反应 Dark Reaction",
         "content_points": ["叶绿体基质", "卡尔文循环", "合成有机物"]},
        {"page_number": 6, "slide_type": "content", "title": "意义 Significance",
         "content_points": ["能量来源", "释放氧气", "支撑生命"]},
        {"page_number": 7, "slide_type": "conclusion", "title": "小结 Summary",
         "content_points": ["两个阶段", "叶绿体中进行", "万物能量之源"]},
    ],
}

FIXTURES = [
    Fixture("strict-material", "outline", "grounded", "teaching", "zh",
            topic="光合作用", material=STRICT_MATERIAL, expected_count=5),
    Fixture("long-material-compression", "outline", "grounded", "teaching", "zh",
            topic="宋代的科技与文化", material=LONG_MATERIAL, expected_count=6),
    Fixture("sundayschool-boundary", "outline", "grounded", "church", "zh",
            topic="好撒玛利亚人", material=SUNDAYSCHOOL_MATERIAL, expected_count=5),
    Fixture("bilingual-notes-count", "notes", "grounded", "teaching", "bilingual",
            material=STRICT_MATERIAL, expected_count=7, outline=NOTES_OUTLINE),
]


# --------------------------------------------------------------------------- #
# Scoring helpers
# --------------------------------------------------------------------------- #
def lenient_json(raw: str):
    raw = (raw or "").strip()
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        if repair_json is not None:
            try:
                return json.loads(repair_json(raw))
            except Exception:
                return None
    return None


_NUM_RE = re.compile(r"\d{2,4}")


def fabrication_numbers(text_blob: str, material: str) -> int:
    """Numbers/years in the output that do NOT appear in the source material."""
    mat_nums = set(_NUM_RE.findall(material))
    out_nums = _NUM_RE.findall(text_blob)
    return sum(1 for n in out_nums if n not in mat_nums)


def has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)


def has_latin(s: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in s)


@dataclass
class Score:
    ok: bool
    count_ok: bool
    raw_count: int
    detail: dict = field(default_factory=dict)


def score_outline(raw_text: str, fix: Fixture, fact_table: list[dict] | None, improved: bool) -> Score:
    data = lenient_json(raw_text)
    slides = data.get("slides", []) if isinstance(data, dict) else []
    raw_count = len(slides)
    count_ok = raw_count == fix.expected_count

    blob = " ".join(
        " ".join(s.get("content_points", []) or []) + " " + str(s.get("title", ""))
        for s in slides if isinstance(s, dict)
    )
    fabr = fabrication_numbers(blob, fix.material)

    detail = {"fabrication_numbers": fabr}
    grounding_ok = None
    if improved and fact_table is not None:
        valid_ids = {f["id"] for f in fact_table}
        invalid = 0
        ungrounded_content = 0
        referenced: set[int] = set()
        for s in slides:
            if not isinstance(s, dict):
                continue
            fids = s.get("fact_ids") or []
            fids = [x for x in fids if isinstance(x, int)]
            for x in fids:
                if x in valid_ids:
                    referenced.add(x)
                else:
                    invalid += 1
            if s.get("slide_type") == "content" and not any(x in valid_ids for x in fids):
                ungrounded_content += 1
        coverage = round(len(referenced) / max(len(valid_ids), 1), 2)
        grounding_ok = invalid == 0 and ungrounded_content == 0
        detail.update({"invalid_ids": invalid, "ungrounded_content": ungrounded_content,
                       "coverage": coverage, "grounding_ok": grounding_ok})

    ok = count_ok and fabr == 0 and (grounding_ok is not False)
    return Score(ok=ok, count_ok=count_ok, raw_count=raw_count, detail=detail)


def score_notes(raw_text: str, fix: Fixture) -> Score:
    data = lenient_json(raw_text)
    notes = data.get("notes", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    notes = [str(n) for n in notes]
    raw_count = len(notes)
    count_ok = raw_count == fix.expected_count
    bilingual_ok = bool(notes) and all(has_cjk(n) and has_latin(n) for n in notes)
    ok = count_ok and bilingual_ok
    return Score(ok=ok, count_ok=count_ok, raw_count=raw_count,
                 detail={"bilingual_ok": bilingual_ok})


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def run_cell(fix: Fixture, improved: bool, temperature: float) -> Score:
    mode = fix.mode if improved else "creative"
    if fix.kind == "outline":
        fact_table = None
        if improved and fix.material:
            fact_table = client.extract_facts(fix.material, temperature=0.0)
        res = client.generate_outline_text(
            topic=fix.topic, num_slides=fix.expected_count, scenario=fix.scenario,
            output_language=fix.language, reference_text=fix.material,
            temperature=temperature, mode=mode, fact_table=fact_table,
        )
        return score_outline(res.raw_text, fix, fact_table, improved)
    else:
        fact_table = None
        if improved and fix.material:
            fact_table = client.extract_facts(fix.material, temperature=0.0)
        res = client.generate_speaker_notes(
            outline=fix.outline, output_language=fix.language, duration_minutes=10,
            style="classroom", article=fix.material,
            temperature=temperature, mode=mode, fact_table=fact_table,
        )
        return score_notes(res.raw_text, fix)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="siliconflow", help="comma list: siliconflow,gemma")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--smoke", action="store_true", help="1 model x 1 cell x 1 item x 1 rep")
    args = ap.parse_args()

    model_keys = ["siliconflow"] if args.smoke else [m.strip() for m in args.models.split(",") if m.strip()]
    cells = [(False, 0.7)] if args.smoke else [(False, 0.7), (False, 0.2), (True, 0.7), (True, 0.2)]
    fixtures = FIXTURES[:1] if args.smoke else FIXTURES
    reps = 1 if args.smoke else args.reps

    def cell_name(improved, temp):
        return f"{'improved' if improved else 'legacy'}@{temp}"

    results: dict = {}
    for mkey in model_keys:
        spec = MODELS.get(mkey)
        if not spec or not spec["api_key"] and mkey == "siliconflow":
            print(f"[skip] {mkey}: missing key/spec")
            continue
        apply_model(spec)
        print(f"\n=== MODEL: {spec['label']} ===")
        for fix in fixtures:
            for improved, temp in cells:
                passes = 0
                notes = []
                for r in range(reps):
                    t = time.perf_counter()
                    try:
                        sc = run_cell(fix, improved, temp)
                        dt = time.perf_counter() - t
                        passes += 1 if sc.ok else 0
                        notes.append(f"{'P' if sc.ok else 'F'}(n={sc.raw_count}/{fix.expected_count},{dt:.0f}s,{sc.detail})")
                    except Exception as e:
                        notes.append(f"ERR {type(e).__name__}: {str(e)[:80]}")
                key = (spec["label"], fix.name, cell_name(improved, temp))
                results[key] = (passes, reps, notes)
                print(f"  [{fix.name:26}] {cell_name(improved,temp):14} -> {passes}/{reps}  {notes}")

    # Markdown report
    out_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "quality" / "prompt-experiment"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"{stamp}-factorial.md"
    lines = [f"# Prompt × Temperature factorial — {stamp}", "",
             f"reps per cell: {reps}", "",
             "| model | item | cell | pass-rate |", "|---|---|---|---|"]
    for (model, item, cell), (p, n, _notes) in results.items():
        lines.append(f"| {model} | {item} | {cell} | {p}/{n} |")
    lines += ["", "## Raw notes", ""]
    for (model, item, cell), (p, n, ns) in results.items():
        lines.append(f"- **{model} / {item} / {cell}**: {p}/{n} — {ns}")
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {out_file}")


if __name__ == "__main__":
    main()
