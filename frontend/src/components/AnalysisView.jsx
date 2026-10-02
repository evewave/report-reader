import React from "react";
import ChartCard from "./ChartCard.jsx";

function ListCard({ title, items, onJump }) {
  if (!items || !items.length) return null;
  return (
    <div className="card">
      <h3>{title}</h3>
      {items.map((it, i) => (
        <div className="list-item" key={i}>
          {it.title && <div className="lt">{it.title}</div>}
          <div>{it.text}</div>
        </div>
      ))}
    </div>
  );
}

function Sections({ sections, onJump }) {
  if (!sections || !sections.length) return null;
  return (
    <div className="card">
      <h3>章节导览 <span className="hint">点击页码跳转原文</span></h3>
      {sections.map((s, i) => (
        <div className="list-item" key={i}>
          <div className="lt">
            {s.heading}{" "}
            {s.page != null && <button className="jump" onClick={() => onJump(s.page)}>第 {s.page} 页 →</button>}
          </div>
          <div>{s.summary}</div>
        </div>
      ))}
    </div>
  );
}

function DataTables({ tables, onJump }) {
  if (!tables || !tables.length) return null;
  return (
    <div className="card">
      <h3>数据表 <span className="hint">{tables.length} 张</span></h3>
      {tables.map((t, i) => (
        <div key={i} style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>
            {t.title}{" "}
            {t.source_page != null && <button className="jump" onClick={() => onJump(t.source_page)}>第 {t.source_page} 页 →</button>}
            {t.note && <span className="hint"> · {t.note}</span>}
          </div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>{(t.headers || []).map((h, j) => <th key={j}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {(t.rows || []).map((row, j) => (
                  <tr key={j}>{row.map((c, k) => <td key={k}>{c}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalysisView({ analysis, onJump }) {
  const r = analysis.result || {};
  const meta = r.meta || {};
  const exportBase = `/api/analyses/${analysis.id}/export`;
  return (
    <div>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <span className="badge">{analysis.skill_id}</span>
          {meta.model && <span className="badge">模型 {meta.model}</span>}
          {meta.vision_used && <span className="badge vision">已用视觉识别图表</span>}
          {meta.vision_error && <span className="badge est">视觉校正失败，用文本结果</span>}
          <span className="hint">分析于 {meta.analyzed_at}</span>
          <span style={{ flex: 1 }} />
          <a className="btn small" href={`${exportBase}?inline=1`} target="_blank" rel="noopener noreferrer">🔍 预览 HTML</a>
          <a className="btn small primary" href={exportBase} download>📤 导出 HTML</a>
        </div>
        <h3>总体概述</h3>
        <div className="summary">{r.summary || "（无概述）"}</div>
      </div>

      {r.metrics?.length > 0 && (
        <div className="card">
          <h3>关键指标</h3>
          <div className="metrics">
            {r.metrics.map((m, i) => (
              <div className="metric" key={i}>
                <div className="label">{m.label}</div>
                <div className="value">
                  {m.value}
                  {m.unit && <span className="unit">{m.unit}</span>}
                </div>
                {m.delta && <div className="delta">{m.delta}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {r.figures?.length > 0 && (
        <div className="card">
          <h3>数据图表 <span className="hint">{r.figures.length} 张 · 可交互，点击「定位」跳回原文</span></h3>
          <div className="charts">
            {r.figures.map((f) => (
              <ChartCard key={f.id || f.title} figure={f} onJump={onJump} />
            ))}
          </div>
        </div>
      )}

      <ListCard title="核心要点" items={r.key_points} />
      <Sections sections={r.sections} onJump={onJump} />
      <DataTables tables={r.tables} onJump={onJump} />
      <ListCard title="风险提示" items={r.risks} />

      {r.questions?.length > 0 && (
        <div className="card">
          <h3>值得进一步追问</h3>
          <ol style={{ paddingLeft: 20, margin: 0 }}>
            {r.questions.map((q, i) => <li key={i} style={{ marginBottom: 4 }}>{q}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}
