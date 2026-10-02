"""把一份分析结果导出为「自包含、可离线打开/分享」的单文件 HTML。

- 内联本地 echarts.min.js（缺失时回退 CDN），图表可交互（悬停/图例/数据视图/存图）。
- 正文/指标/表格/要点等由后端直接渲染成 HTML（无 JS 也能阅读、可打印）；仅图表脚本负责画图。
"""
from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import ROOT_DIR

ECHARTS_LOCAL = ROOT_DIR / "frontend" / "node_modules" / "echarts" / "dist" / "echarts.min.js"
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"


@lru_cache(maxsize=1)
def _echarts_source() -> tuple[str, bool]:
    """返回 (脚本内容, 是否内联)。内联则导出文件完全离线。"""
    try:
        if ECHARTS_LOCAL.exists():
            return ECHARTS_LOCAL.read_text(encoding="utf-8"), True
    except (OSError, UnicodeDecodeError):
        pass
    return "", False


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


_STYLE = """
:root{--bg:#eef1f8;--surface:#fff;--surface2:#f6f7fb;--border:#e6e8f0;--text:#1b2130;--muted:#6b7488;--accent:#5b6cff;--accent2:#8b5cf6;--ok:#15a34a;--warn:#b45309}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",Roboto,Helvetica,Arial,sans-serif;color:var(--text);background:var(--bg);line-height:1.7;font-size:14px}
.wrap{max-width:1080px;margin:0 auto;padding:28px 22px 60px}
.hero{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-radius:16px;padding:24px 26px;margin-bottom:20px;box-shadow:0 8px 28px rgba(80,90,180,.25)}
.hero h1{margin:0 0 8px;font-size:22px;line-height:1.35}
.hero .tags{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;opacity:.92}
.hero .tags span{background:rgba(255,255,255,.18);padding:2px 10px;border-radius:999px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;margin-bottom:16px;box-shadow:0 1px 2px rgba(20,24,40,.05)}
h2{font-size:16px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
h2::before{content:"";width:4px;height:15px;border-radius:3px;background:linear-gradient(var(--accent),var(--accent2))}
.summary{font-size:15px}
.metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.metric{border:1px solid var(--border);border-radius:10px;padding:12px;background:var(--surface2)}
.metric .l{color:var(--muted);font-size:12px}.metric .v{font-size:21px;font-weight:800}.metric .u{font-size:12px;color:var(--muted);font-weight:400;margin-left:3px}.metric .d{font-size:12px;color:var(--ok)}
.charts{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}
.fig{border:1px solid var(--border);border-radius:12px;padding:12px;background:var(--surface)}
.fig .h{display:flex;align-items:center;gap:8px;font-weight:700;margin-bottom:6px}
.chart{width:100%;height:320px}.chart .err{color:var(--muted);text-align:center;padding:40px}
.badge{font-size:11px;padding:1px 8px;border-radius:999px;border:1px solid var(--border);color:var(--muted)}
.badge.est{color:var(--warn);border-color:#ecdca6;background:#fbf5e6}
.badge.pg{color:var(--accent);border-color:#c5d6ff;background:#eaedff}
.insight{font-size:12.5px;color:var(--muted);margin-top:6px;background:var(--surface2);border-radius:8px;padding:7px 9px}
.item{padding:9px 0;border-bottom:1px dashed var(--border)}.item:last-child{border:none}.item .t{font-weight:700}
table{width:100%;border-collapse:collapse;font-size:13px}.tw{overflow-x:auto}th,td{border:1px solid var(--border);padding:7px 9px;text-align:left}th{background:var(--surface2)}
ol{padding-left:22px;margin:0}li{margin:4px 0}
.foot{color:var(--muted);font-size:12px;text-align:center;margin-top:24px}
@media print{body{background:#fff}.chart{break-inside:avoid}.card,.fig,.hero{box-shadow:none}}
"""

_SCRIPT = """
function buildOption(fig){
  var cats=fig.categories||[], series=fig.series||[], type=fig.chart_type||'line';
  var base={color:["#5b6cff","#ff7a45","#16a34a","#a855f7","#e5484d","#0e97ad","#d98600"],
    tooltip:{trigger:'axis',confine:true},legend:{type:'scroll',bottom:0},
    grid:{left:48,right:48,top:36,bottom:54,containLabel:true},
    toolbox:{feature:{saveAsImage:{title:'保存图片'},dataView:{title:'数据表'}}}};
  if(type==='pie'){var d=((series[0]&&series[0].data)||[]).map(function(v,i){return{name:cats[i]||('项'+(i+1)),value:v};});
    return Object.assign({},base,{tooltip:{trigger:'item',confine:true},legend:{bottom:0,type:'scroll'},series:[{type:'pie',radius:['40%','66%'],center:['50%','45%'],data:d,label:{formatter:'{b}\\n{d}%'}}]});}
  if(type==='radar'){var ind=cats.map(function(c,i){var mx=0;series.forEach(function(s){var v=(s.data||[])[i];if(typeof v==='number')mx=Math.max(mx,v);});return{name:c,max:mx>0?Math.ceil(mx*1.1):1};});
    return Object.assign({},base,{tooltip:{trigger:'item',confine:true},radar:{indicator:ind,radius:'60%',center:['50%','48%']},series:[{type:'radar',data:series.map(function(s){return{name:s.name,value:s.data||[]};})}]});}
  var two=series.some(function(s){return Number(s.yAxisIndex)===1;});
  function ax(n){return{type:'value',name:n||''};}
  var y=two?[ax(fig.unit),{type:'value',splitLine:{show:false}}]:[ax(fig.unit)];
  return Object.assign({},base,{
    xAxis:{type:'category',data:cats,axisLabel:{interval:'auto',rotate:cats.length>7?30:0}},
    yAxis:y,
    series:series.map(function(s){var t=s.type==='area'?'line':(s.type||type);return{name:s.name,type:t,yAxisIndex:Number(s.yAxisIndex)||0,smooth:t==='line',areaStyle:s.type==='area'?{opacity:.18}:undefined,symbol:t==='scatter'?'circle':undefined,barMaxWidth:34,data:s.data||[]};})
  });
}
document.querySelectorAll('.chart').forEach(function(el){
  try{var fig=JSON.parse(el.getAttribute('data-fig'));var c=echarts.init(el);c.setOption(buildOption(fig));
    window.addEventListener('resize',function(){c.resize();});}
  catch(e){el.innerHTML='<div class="err">图表渲染失败：'+(e.message||e)+'</div>';}
});
"""


def _fig_block(f: dict[str, Any]) -> str:
    data = json.dumps(f, ensure_ascii=False).replace("</", "<\\/")
    badges = ""
    if f.get("estimated"):
        badges += '<span class="badge est">≈ 近似</span>'
    if f.get("source_page"):
        badges += f'<span class="badge pg">第 {_esc(f["source_page"])} 页</span>'
    insight = f'<div class="insight">💡 {_esc(f.get("insight"))}</div>' if f.get("insight") else ""
    return (
        '<div class="fig"><div class="h">'
        f'<span>{_esc(f.get("title"))}</span>{badges}</div>'
        f'<div class="chart" data-fig=\'{html.escape(data, quote=True)}\'></div>{insight}</div>'
    )


def _metric_block(m: dict[str, Any]) -> str:
    delta = f'<div class="d">{_esc(m.get("delta"))}</div>' if m.get("delta") else ""
    return (
        f'<div class="metric"><div class="l">{_esc(m.get("label"))}</div>'
        f'<div class="v">{_esc(m.get("value"))}<span class="u">{_esc(m.get("unit"))}</span></div>{delta}</div>'
    )


def _section_block(s: dict[str, Any]) -> str:
    page = f' <span class="badge pg">第 {_esc(s.get("page"))} 页</span>' if s.get("page") else ""
    return (
        f'<div class="item"><div class="t">{_esc(s.get("heading"))}{page}</div>'
        f'<div>{_esc(s.get("summary"))}</div></div>'
    )


def _pt_card(title: str, items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    parts = []
    for it in items:
        head = f'<div class="t">{_esc(it.get("title"))}</div>' if it.get("title") else ""
        parts.append(f'<div class="item">{head}<div>{_esc(it.get("text"))}</div></div>')
    return f'<div class="card"><h2>{_esc(title)}</h2>{"".join(parts)}</div>'


def _table_card(tables: list[dict[str, Any]]) -> str:
    if not tables:
        return ""
    blocks = ""
    for t in tables:
        head = "".join(f"<th>{_esc(h)}</th>" for h in (t.get("headers") or []))
        body = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in (row or [])) + "</tr>" for row in (t.get("rows") or []))
        pg = f' <span class="badge pg">第 {_esc(t.get("source_page"))} 页</span>' if t.get("source_page") else ""
        blocks += (
            f'<div style="margin-bottom:16px"><div style="font-weight:700;margin-bottom:6px">{_esc(t.get("title"))}{pg}</div>'
            f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></div>'
        )
    return f'<div class="card"><h2>数据表</h2>{blocks}</div>'


def build_html(result: dict[str, Any]) -> str:
    meta = result.get("meta", {}) or {}
    title = meta.get("title") or "研报精读"
    figures = result.get("figures", []) or []
    metrics = result.get("metrics", []) or []
    sections = result.get("sections", []) or []
    questions = result.get("questions", []) or []

    tags = [f"技能 {_esc(meta.get('skill_id'))}", f"模型 {_esc(meta.get('model'))}"]
    if meta.get("vision_used"):
        tags.append("含视觉识别")
    if meta.get("page_count"):
        tags.append(f"{meta.get('page_count')} 页")

    metric_html = "".join(_metric_block(m) for m in metrics)
    figs_html = "".join(_fig_block(f) for f in figures)
    sections_html = "".join(_section_block(s) for s in sections)

    figs_card = (
        f'<div class="card"><h2>数据图表 <span class="badge">{len(figures)} 张 · 可交互</span></h2>'
        f'<div class="charts">{figs_html}</div></div>' if figs_html else ""
    )
    metrics_card = f'<div class="card"><h2>关键指标</h2><div class="metrics">{metric_html}</div></div>' if metric_html else ""
    sections_card = f'<div class="card"><h2>章节导览</h2>{sections_html}</div>' if sections_html else ""
    tables_card = _table_card(result.get("tables", []) or [])
    q_card = (
        f'<div class="card"><h2>值得进一步追问</h2><ol>{"".join(f"<li>{_esc(q)}</li>" for q in questions)}</ol></div>'
        if questions else ""
    )

    js_src, inlined = _echarts_source()
    echarts_tag = f"<script>{js_src}</script>" if inlined else f'<script src="{ECHARTS_CDN}"></script>'
    hero_tags = "".join(f"<span>{t}</span>" for t in tags)

    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{_esc(title)}</title><style>{_STYLE}</style>{echarts_tag}</head>"
        f"<body><div class=\"wrap\">"
        f"<div class=\"hero\"><h1>{_esc(title)}</h1><div class=\"tags\">{hero_tags}</div></div>"
        f"<div class=\"card\"><h2>总体概述</h2><div class=\"summary\">{_esc(result.get('summary'))}</div></div>"
        f"{metrics_card}{figs_card}{_pt_card('核心要点', result.get('key_points') or [])}{sections_card}{tables_card}"
        f"{_pt_card('风险提示', result.get('risks') or [])}{q_card}"
        f"<div class=\"foot\">由「研报 AI 阅读助手」生成 · {_esc(meta.get('analyzed_at'))} · {'离线版' if inlined else '在线版'}</div>"
        f"</div><script>{_SCRIPT}</script></body></html>"
    )


def safe_filename(title: str) -> str:
    cleaned = "".join(c for c in (title or "report") if c not in '\\/:*?"<>|').strip()
    return f"{(cleaned or 'report')[:60]}-精读.html"
