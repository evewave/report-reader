"""分析编排：把 PDF 抽取结果 + skill 模板 喂给 OpenAI，产出前端可直接渲染的规范化结构。

产出 result schema（前端 ChartCard / 面板依赖）：
{
  "meta": {...},
  "summary": str,
  "metrics": [{"label","value","unit","delta"}],
  "key_points": [{"title","text"}],
  "sections": [{"heading","summary","page"}],
  "figures": [{"id","title","chart_type","source_page","unit","categories":[],"series":[{"name","type","yAxisIndex","data":[]}],"insight","estimated":bool}],
  "tables": [{"title","source_page","headers":[],"rows":[[]],"note"}],
  "risks": [{"title","text"}],
  "questions": [str]
}
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import PAGES_DIR, UPLOAD_DIR, settings
from . import ai_service, skill_loader

VALID_CHART_TYPES = {"line", "bar", "pie", "area", "scatter", "radar"}
VALID_SERIES_TYPES = {"line", "bar", "pie", "area", "scatter", "radar"}

SYSTEM_BASE = (
    "你是资深金融/学术研报阅读助手，服务于「把静态研报转成可交互 HTML 阅读体验」的工具。"
    "你只输出一个 JSON 对象，不要任何解释文字、不要 Markdown 代码块以外的内容。"
    "所有数字必须来自给定材料，不得臆造；无法确定的图表数值请标 \"estimated\": true 并给出你能得到的最接近近似。"
)

OUTPUT_SPEC = """输出 JSON 必须严格符合以下结构（字段缺省用空数组/空串）：
{
  "summary": "3-6句总体概述这份研报讲了什么、核心结论",
  "metrics": [{"label":"指标名","value":"数值","unit":"单位","delta":"同比/变化，可为空"}],
  "key_points": [{"title":"要点标题","text":"要点说明"}],
  "sections": [{"heading":"章节/小节标题","summary":"该部分讲了什么","page":页码整数或null}],
  "figures": [
    {"id":"f1","title":"图表标题","chart_type":"line|bar|pie|area|scatter|radar",
     "source_page":页码整数或null,"unit":"纵轴单位",
     "categories":["x轴标签或饼图分类"],
     "series":[{"name":"系列名","type":"line|bar|area","yAxisIndex":0或1,"data":[数值,可含null]}],
     "insight":"这张图说明了什么","estimated":false}
  ],
  "tables": [{"title":"表标题","source_page":页码或null,"headers":["列名"],"rows":[["单元格"]],"note":"备注"}],
  "risks": [{"title":"风险点","text":"说明"}],
  "questions": ["值得进一步深挖/存疑的问题"]
}
说明：figures 只放「有明确数值、可画图」的数据；pie 用单一 series + categories 作为切片。"""


def _doc_extract_path(doc_id: str) -> Path:
    return UPLOAD_DIR / f"{doc_id}.json"


def load_extract(doc_id: str) -> dict[str, Any]:
    p = _doc_extract_path(doc_id)
    if not p.exists():
        raise FileNotFoundError(f"缺少抽取结果：{doc_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def _flatten_text(extract: dict[str, Any], limit: int) -> str:
    chunks: list[str] = []
    total = 0
    for pg in extract["pages"]:
        if not pg["text"]:
            continue
        block = f"\n[第 {pg['page']} 页]\n{pg['text']}"
        chunks.append(block)
        total += len(block)
        if total >= limit:
            chunks.append("\n（正文过长，后续页已截断；请基于已提供内容作答）")
            break
    return "".join(chunks)


def _tables_text(extract: dict[str, Any], max_tables: int = 40) -> str:
    out: list[str] = []
    for i, t in enumerate(extract["tables"][:max_tables]):
        head = f"\n[表格@第{t['page']}页]"
        rows = "\n".join(" | ".join(r) for r in t["rows"][:60])
        out.append(f"{head}\n{rows}")
    return "\n".join(out) if out else "（未抽取到规整表格，请从正文中识别可量化数据）"


def _chart_pages(extract: dict[str, Any], max_pages: int = 6) -> list[int]:
    counts = extract.get("page_image_counts", [])
    ranked = sorted(enumerate(counts, start=1), key=lambda x: x[1], reverse=True)
    return [page for page, c in ranked if c > 0][:max_pages]


def _normalize_result(raw: dict[str, Any], skill_id: str, model: str, extract: dict[str, Any]) -> dict[str, Any]:
    def _as_list(v: Any) -> list:
        return v if isinstance(v, list) else []

    figures: list[dict[str, Any]] = []
    for idx, f in enumerate(_as_list(raw.get("figures"))):
        if not isinstance(f, dict):
            continue
        chart_type = str(f.get("chart_type", "line")).lower()
        if chart_type not in VALID_CHART_TYPES:
            chart_type = "line"
        series: list[dict[str, Any]] = []
        for s in _as_list(f.get("series")):
            if not isinstance(s, dict):
                continue
            data = [x if isinstance(x, (int, float)) or x is None else _to_num(x) for x in _as_list(s.get("data"))]
            stype = str(s.get("type", chart_type)).lower()
            series.append({
                "name": str(s.get("name", f"系列{len(series) + 1}")),
                "type": stype if stype in VALID_SERIES_TYPES else chart_type,
                "yAxisIndex": int(s.get("yAxisIndex", 0) or 0),
                "data": data,
            })
        cats = f.get("categories")
        figures.append({
            "id": str(f.get("id") or f"f{idx + 1}"),
            "title": str(f.get("title", f"图表 {idx + 1}")),
            "chart_type": chart_type,
            "source_page": _to_int(f.get("source_page")),
            "unit": str(f.get("unit", "")),
            "categories": [str(c) for c in _as_list(cats)],
            "series": series,
            "insight": str(f.get("insight", "")),
            "estimated": bool(f.get("estimated", False)),
        })

    tables = []
    for t in _as_list(raw.get("tables")):
        if not isinstance(t, dict):
            continue
        tables.append({
            "title": str(t.get("title", "数据表")),
            "source_page": _to_int(t.get("source_page")),
            "headers": [str(h) for h in _as_list(t.get("headers"))],
            "rows": [[("" if c is None else str(c)) for c in _as_list(r)] for r in _as_list(t.get("rows"))],
            "note": str(t.get("note", "")),
        })

    def _pt_list(key: str) -> list[dict[str, str]]:
        res = []
        for x in _as_list(raw.get(key)):
            if isinstance(x, dict):
                res.append({"title": str(x.get("title", "")), "text": str(x.get("text", ""))})
            elif isinstance(x, str):
                res.append({"title": "", "text": x})
        return res

    sections = []
    for s in _as_list(raw.get("sections")):
        if isinstance(s, dict):
            sections.append({"heading": str(s.get("heading", "")), "summary": str(s.get("summary", "")), "page": _to_int(s.get("page"))})

    metrics = []
    for m in _as_list(raw.get("metrics")):
        if isinstance(m, dict):
            metrics.append({"label": str(m.get("label", "")), "value": str(m.get("value", "")), "unit": str(m.get("unit", "")), "delta": str(m.get("delta", ""))})

    return {
        "meta": {
            "title": extract.get("title", ""),
            "skill_id": skill_id,
            "model": model,
            "page_count": extract.get("page_count", 0),
            "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vision_used": False,
        },
        "summary": str(raw.get("summary", "")),
        "metrics": metrics,
        "key_points": _pt_list("key_points"),
        "sections": sections,
        "figures": figures,
        "tables": tables,
        "risks": _pt_list("risks"),
        "questions": [str(q) for q in _as_list(raw.get("questions"))],
    }


def _to_num(x: Any) -> float | None:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        return float(s) if s not in {"", "-", "—", "N/A", "n/a", "None"} else None
    except (ValueError, TypeError):
        return None


def _to_int(x: Any) -> int | None:
    n = _to_num(x)
    return int(n) if n is not None else None


def _vision_refine(figures: list[dict[str, Any]], pages: list[int], extract: dict[str, Any]) -> list[dict[str, Any]]:
    """把含图的页面截图交给视觉模型，校正/补全 figures 的数值。"""
    page_dir = PAGES_DIR / extract["doc_id"]
    images = [page_dir / f"page_{p:04d}.png" for p in pages]
    images = [i for i in images if i.exists()]
    if not images:
        return figures
    ask = (
        "下面依次给出研报中的若干图表页截图（顺序对应页码："
        + ",".join(str(p) for p in pages)
        + "）。请只针对这些页里的图表，尽量精确读出数值，修正下列已有图表条目的 categories/series/数值与 source_page。"
        "保持 id 不变；读不出的保留原值并把 estimated 设为 true。"
        "只输出一个 JSON，形如 {\"figures\": [ 同结构的图表条目数组 ]}。\n\n现有条目：\n"
        + json.dumps([{"id": f["id"], "title": f["title"], "source_page": f["source_page"]} for f in figures], ensure_ascii=False)
    )
    data = ai_service.ask_json(
        SYSTEM_BASE + " 你在做图表数据识别，优先准确读出坐标轴、刻度与数据点。",
        ask,
        images=images,
    )
    refined = data.get("figures")
    if not isinstance(refined, list):
        return figures
    by_id = {f["id"]: f for f in figures}
    for r in refined:
        if isinstance(r, dict) and str(r.get("id")) in by_id:
            merged = _normalize_result({"figures": [r]}, "x", "x", {"doc_id": extract["doc_id"]})["figures"][0]
            target = by_id[str(r["id"])]
            if merged["categories"] or merged["series"]:
                target["categories"] = merged["categories"] or target["categories"]
                target["series"] = merged["series"] or target["series"]
                if merged["source_page"]:
                    target["source_page"] = merged["source_page"]
                target["estimated"] = merged["estimated"]
    return figures


def run_analysis(doc_id: str, skill_id: str, use_vision: bool | None = None) -> dict[str, Any]:
    skill = skill_loader.get(skill_id)
    if not skill:
        raise ValueError(f"未找到 skill：{skill_id}")
    extract = load_extract(doc_id)

    if use_vision is None:
        use_vision = bool(skill["needs_vision"])

    values = {
        "title": extract.get("title", ""),
        "doc_title": extract.get("title", ""),
        "n_pages": str(extract.get("page_count", 0)),
        "text": _flatten_text(extract, settings.MAX_TEXT_CHARS),
        "tables": _tables_text(extract),
        "pages_json": json.dumps([{"page": p["page"], "chars": p["chars"]} for p in extract["pages"]], ensure_ascii=False),
        "instructions": skill.get("instructions", ""),
        "chart_hints": skill.get("chart_hints", ""),
    }
    user_prompt = skill_loader.fill_prompt(skill["prompt_template"], values) + "\n\n" + OUTPUT_SPEC

    model = ai_service.default_model()
    raw = ai_service.ask_json(
        SYSTEM_BASE + "\n\n分析侧重：\n" + (skill.get("instructions", "")[:2000] or skill.get("description", "")),
        user_prompt,
        model=model,
    )
    result = _normalize_result(raw, skill_id, model, extract)

    if use_vision and result["figures"]:
        try:
            pages = _chart_pages(extract)
            result["figures"] = _vision_refine(result["figures"], pages, extract)
            result["meta"]["vision_used"] = True
            result["meta"]["vision_model"] = ai_service.default_vision_model()
        except ai_service.AiNotConfigured:
            raise
        except Exception as exc:  # noqa: BLE001 - 视觉校正失败不影响主结果
            result["meta"]["vision_error"] = str(exc)

    return result
