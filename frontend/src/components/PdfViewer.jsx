import React, { useEffect, useRef, useState } from "react";
import { pageImageUrl, pdfUrl, annotatedPdfUrl, getAnnotations, saveAnnotations, deleteAnnotations, getTextLayer } from "../api.js";

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const DEFAULT_COLOR = { highlight: "#ffe14d", underline: "#e5484d", strike: "#e5484d", rect: "#5b6cff", note: "#f59e0b" };
const BOX_TOOLS = ["highlight", "underline", "strike", "rect"];
const TYPE_ICON = { highlight: "🖍", underline: "🟘", strike: "🚫", rect: "▭", note: "📝" };
const TYPE_CN = { highlight: "高亮", underline: "下划线", strike: "删除线", rect: "框选", note: "便签" };

function rectStyle(rect, type, color) {
  const [x0, y0, x1, y1] = rect;
  const left = Math.min(x0, x1) * 100, top = Math.min(y0, y1) * 100;
  const w = Math.abs(x1 - x0) * 100, h = Math.abs(y1 - y0) * 100;
  const base = { position: "absolute", left: `${left}%`, top: `${top}%`, width: `${w}%`, height: `${h}%` };
  const c = color || "#ffe14d";
  if (type === "highlight") return { ...base, background: c, opacity: 0.38, mixBlendMode: "multiply" };
  if (type === "underline") return { ...base, borderBottom: `2px solid ${c}` };
  if (type === "strike") return { ...base, background: `linear-gradient(transparent calc(50% - 1px), ${c} calc(50% - 1px), ${c} calc(50% + 1px), transparent calc(50% + 1px))` };
  if (type === "rect") return { ...base, border: `2px solid ${c}` };
  return base;
}
const itemRects = (it) => (Array.isArray(it.rects) && it.rects.length ? it.rects : (it.box ? [it.box] : []));
const intersects = (a, b) => !(a[2] < b[0] || b[2] < a[0] || a[3] < b[1] || b[3] < a[1]);
function mergeLines(boxes) {
  const sorted = [...boxes].sort((p, q) => p[1] - q[1] || p[0] - q[0]);
  const lines = [];
  for (const b of sorted) {
    const ln = lines.find((L) => Math.abs(L[1] - b[1]) < 0.006);
    if (ln) { ln[0] = Math.min(ln[0], b[0]); ln[1] = Math.min(ln[1], b[1]); ln[2] = Math.max(ln[2], b[2]); ln[3] = Math.max(ln[3], b[3]); }
    else lines.push([b[0], b[1], b[2], b[3]]);
  }
  return lines;
}

export default function PdfViewer({ docId, pageCount, jump, docTitle, focusMode }) {
  const [zoom, setZoom] = useState(2);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [layers, setLayers] = useState({});
  const [mode, setMode] = useState("view");
  const [color, setColor] = useState(DEFAULT_COLOR.highlight);
  const [selectedId, setSelectedId] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [draft, setDraft] = useState(null);
  const [hasAnnotated, setHasAnnotated] = useState(false);
  const [listOpen, setListOpen] = useState(() => { try { return localStorage.getItem("rr-annolist") === "1"; } catch (_) { return false; } });
  const [barOpen, setBarOpen] = useState(() => { try { return localStorage.getItem("rr-annobar") !== "0"; } catch (_) { return true; } });
  const [selPopup, setSelPopup] = useState(null); // {page, rects, text, left, top}

  const scrollRef = useRef(null);
  const pageRefs = useRef({});
  const wrapRefs = useRef({});
  const drawRef = useRef(null);

  useEffect(() => { setPage(1); setSelPopup(null); }, [docId]);

  useEffect(() => {
    let alive = true;
    getAnnotations(docId).then((d) => { if (!alive) return; const its = d.items || []; setItems(its); setDirty(false); setHasAnnotated(its.length > 0); }).catch(() => {});
    getTextLayer(docId).then((d) => { if (!alive) return; const m = {}; (d.pages || []).forEach((p) => { m[p.page] = p.words || []; }); setLayers(m); }).catch(() => setLayers({}));
    return () => { alive = false; };
  }, [docId]);

  useEffect(() => {
    if (!jump || !jump.page) return;
    const el = pageRefs.current[jump.page];
    if (el && scrollRef.current) {
      scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
      el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 1200); setPage(jump.page);
    }
  }, [jump]);

  useEffect(() => { try { localStorage.setItem("rr-annolist", listOpen ? "1" : "0"); } catch (_) {} }, [listOpen]);
  useEffect(() => { try { localStorage.setItem("rr-annobar", barOpen ? "1" : "0"); } catch (_) {} }, [barOpen]);

  const annotating = BOX_TOOLS.includes(mode);
  const barVisible = barOpen && !focusMode;

  const goTo = (p) => {
    p = Math.min(Math.max(1, p), pageCount);
    const el = pageRefs.current[p];
    if (el && scrollRef.current) scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
    setPage(p);
  };

  // —— 拖框（图表等无文本区域）——
  const norm = (e, layer) => { const r = layer.getBoundingClientRect(); return [clamp01((e.clientX - r.left) / r.width), clamp01((e.clientY - r.top) / r.height)]; };
  const onPointerDown = (e, p) => {
    if (!annotating) return;
    const [nx, ny] = norm(e, e.currentTarget);
    e.currentTarget.setPointerCapture?.(e.pointerId);
    drawRef.current = { page: p, type: mode, x0: nx, y0: ny };
    setDraft({ page: p, type: mode, box: [nx, ny, nx, ny] });
  };
  const onPointerMove = (e, p) => {
    if (!drawRef.current || drawRef.current.page !== p) return;
    const [nx, ny] = norm(e, e.currentTarget);
    setDraft({ page: p, type: drawRef.current.type, box: [drawRef.current.x0, drawRef.current.y0, nx, ny] });
  };
  const onPointerUp = (e, p) => {
    if (!drawRef.current) return;
    const d = drawRef.current; drawRef.current = null;
    const [nx, ny] = norm(e, e.currentTarget);
    setDraft(null);
    if (Math.abs(nx - d.x0) < 0.005 && Math.abs(ny - d.y0) < 0.005) return;
    setItems((its) => [...its, { id: uid(), page: p, type: d.type, box: [d.x0, d.y0, nx, ny], color }]);
    setDirty(true);
  };

  // —— 选中文本 → 弹批注菜单 ——
  const onMouseUpPage = (p) => {
    if (annotating) return;
    setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount) { setSelPopup(null); return; }
      const wrap = wrapRefs.current[p]; if (!wrap) return;
      const wr = wrap.getBoundingClientRect(); if (wr.width <= 0 || wr.height <= 0) return;
      const range = sel.getRangeAt(0);
      const clientRects = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
      if (!clientRects.length) { setSelPopup(null); return; }
      const normRects = clientRects.map((r) => [(r.left - wr.left) / wr.width, (r.top - wr.top) / wr.height, (r.right - wr.left) / wr.width, (r.bottom - wr.top) / wr.height]);
      const words = layers[p] || [];
      const hit = words.filter((wd) => normRects.some((nr) => intersects([wd[0], wd[1], wd[2], wd[3]], nr)));
      if (!hit.length) { setSelPopup(null); return; }
      const rects = mergeLines(hit.map((wd) => [wd[0], wd[1], wd[2], wd[3]]));
      const text = hit.map((wd) => wd[4]).join(" ").replace(/\s+/g, " ").trim();
      const last = clientRects[clientRects.length - 1];
      setSelPopup({ page: p, rects, text, left: Math.min(window.innerWidth - 90, last.left + last.width / 2), top: last.bottom + 6 });
    }, 0);
  };
  const addFromSelection = (type) => {
    if (!selPopup) return;
    if (type === "note") {
      const t = window.prompt("便签内容：", selPopup.text) || "";
      const first = selPopup.rects[0];
      setItems((its) => [...its, { id: uid(), page: selPopup.page, type: "note", pos: [(first[0] + first[2]) / 2, (first[1] + first[3]) / 2], text: t, color: DEFAULT_COLOR.note }]);
    } else {
      setItems((its) => [...its, { id: uid(), page: selPopup.page, type, rects: selPopup.rects, text: selPopup.text, color }]);
    }
    setDirty(true); window.getSelection()?.removeAllRanges(); setSelPopup(null);
  };

  const undo = () => { setItems((its) => its.slice(0, -1)); setDirty(true); setSelectedId(null); };
  const delSelected = () => { if (!selectedId) return; setItems((its) => its.filter((i) => i.id !== selectedId)); setSelectedId(null); setDirty(true); };
  useEffect(() => {
    const onKey = (e) => { const t = e.target.tagName; if (t === "INPUT" || t === "TEXTAREA") return; if (e.key === "Delete" && selectedId) delSelected(); };
    window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const save = async () => { try { await saveAnnotations(docId, items); setDirty(false); setHasAnnotated(items.length > 0); } catch (e) { alert("保存批注失败：" + e.message); } };
  const clearAll = async () => { if (!confirm("清除该文档全部批注？")) return; try { await deleteAnnotations(docId); setItems([]); setDirty(false); setHasAnnotated(false); setSelectedId(null); } catch (e) { alert(e.message); } };
  const editNote = (it) => { const t = window.prompt("编辑便签：", it.text); if (t !== null) { setItems((its) => its.map((x) => x.id === it.id ? { ...x, text: t } : x)); setDirty(true); } };

  const jumpToItem = (it) => { setMode("view"); setSelectedId(it.id); const el = pageRefs.current[it.page]; if (el && scrollRef.current) { scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" }); setPage(it.page); } };

  const buildNotes = () => {
    const byPage = {};
    items.forEach((it) => { (byPage[it.page] = byPage[it.page] || []).push(it); });
    const pages = Object.keys(byPage).map(Number).sort((a, b) => a - b);
    let md = `# 批注笔记 — ${docTitle || "研报"}\n\n> 共 ${items.length} 条批注 · 导出时间 ${new Date().toLocaleString()}\n`;
    for (const pg of pages) {
      md += `\n## 第 ${pg} 页（${byPage[pg].length} 条）\n`;
      for (const it of byPage[pg]) {
        const label = it.type === "note" ? (it.text || "（空便签）") : `**${TYPE_CN[it.type] || it.type}**：${it.text || ""}`;
        md += `- ${TYPE_ICON[it.type] || "•"} ${label}\n`;
      }
    }
    return md;
  };
  const downloadNotes = () => {
    if (!items.length) { alert("还没有批注"); return; }
    const blob = new Blob([buildNotes()], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `${(docTitle || "report").replace(/[\\/:*?"<>|]/g, "").slice(0, 50) || "report"}-批注笔记.md`;
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const copyNotes = async () => { if (!items.length) { alert("还没有批注"); return; } try { await navigator.clipboard.writeText(buildNotes()); alert("已复制批注笔记"); } catch (_) { alert("复制失败，请用「导出 MD」"); } };

  const perPage = (p) => items.filter((i) => i.page === p);
  const tools = [["view", "🖐 选择"], ["highlight", "🖍 高亮"], ["underline", "🟘 下划线"], ["strike", "🚫 删除线"], ["rect", "▭ 框选"]];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }} onMouseDown={() => setSelPopup(null)}>
      {barVisible && (
        <div className="pager anno-bar" onMouseDown={(e) => e.stopPropagation()}>
          <div className="anno-tools">
            {tools.map(([m, label]) => (
              <button key={m} className={"btn small" + (mode === m ? " primary" : "")} onClick={() => { setMode(m); if (m !== "view") setColor(DEFAULT_COLOR[m]); }}>{label}</button>
            ))}
            <button className={"btn small" + (mode === "note" ? " primary" : "")} onClick={() => setMode("note")} title="点击页面添加便签">📝 便签</button>
            {annotating && <input type="color" value={color} onChange={(e) => setColor(e.target.value)} title="批注颜色" style={{ width: 30, height: 28, padding: 0 }} />}
          </div>
          <div className="anno-sep" />
          <div className="anno-nav">
            <button className="btn small" onClick={() => goTo(page - 1)}>上一页</button>
            <input className="btn small" style={{ width: 52, textAlign: "center" }} type="number" min="1" max={pageCount} value={page} onChange={(e) => setPage(e.target.value)} onKeyDown={(e) => e.key === "Enter" && goTo(Number(e.target.value))} />
            <span className="anno-pgnum">/ {pageCount}</span>
            <button className="btn small" onClick={() => goTo(page + 1)}>下一页</button>
            <button className="btn small" onClick={() => setZoom((z) => Math.max(0.6, +(z - 0.2).toFixed(1)))}>－</button>
            <span className="anno-pgnum">{Math.round(zoom * 100)}%</span>
            <button className="btn small" onClick={() => setZoom((z) => Math.min(3, +(z + 0.2).toFixed(1)))}>＋</button>
          </div>
          <div className="anno-sep" />
          <div className="anno-actions">
            <button className="btn small" onClick={undo} disabled={!items.length}>↶ 撤销</button>
            <button className="btn small" onClick={delSelected} disabled={!selectedId}>🗑 删除所选</button>
            <button className="btn small" onClick={clearAll} disabled={!items.length && !hasAnnotated}>清空批注</button>
            <button className={"btn small primary" + (dirty ? " dirty" : "")} onClick={save} disabled={!dirty}>💾 保存批注{dirty ? " ·" : ""}</button>
            <a className="btn small" href={pdfUrl(docId)} download>原始</a>
            <a className={"btn small" + (hasAnnotated ? "" : " disabled")} href={annotatedPdfUrl(docId)} download onClick={(e) => { if (!hasAnnotated) { e.preventDefault(); alert("先保存批注后才会生成批注版 PDF"); } }}>批注版</a>
            <button className={"btn small" + (listOpen ? " primary" : "")} onClick={() => setListOpen((v) => !v)} title="批注列表">📋 列表{items.length ? ` (${items.length})` : ""}</button>
            <button className="btn small ghost" onClick={() => setBarOpen(false)} title="隐藏工具栏">⤒ 隐藏</button>
          </div>
        </div>
      )}
      {!barVisible && !focusMode && (
        <div className="pager anno-bar collapsed">
          <button className="btn small" onClick={() => setBarOpen(true)}>⤓ 工具栏</button>
          <span className="anno-hint">第 {page}/{pageCount} 页 · 选中文本即可批注</span>
        </div>
      )}

      <div className="pdf-body">
        <div ref={scrollRef} className={"pdf-scroll" + (annotating ? " annotating" : "")} onMouseDown={() => setSelPopup(null)}>
          <div className="pdf-view">
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => {
              const list = perPage(p);
              const words = layers[p] || [];
              return (
                <div key={p} className="pdf-page" ref={(el) => (pageRefs.current[p] = el)} style={{ width: 760 * zoom, maxWidth: "96%" }}>
                  <div className="img-wrap" ref={(el) => (wrapRefs.current[p] = el)} onMouseUp={() => onMouseUpPage(p)}>
                    <img src={pageImageUrl(docId, p)} loading="lazy" alt={`第 ${p} 页`} draggable={false} />
                    <div className="textlayer">
                      {words.map((wd, i) => (
                        <span key={i} className="tw" style={{ left: `${wd[0] * 100}%`, top: `${wd[1] * 100}%`, width: `${(wd[2] - wd[0]) * 100}%`, height: `${(wd[3] - wd[1]) * 100}%` }}>{wd[4]}</span>
                      ))}
                    </div>
                    <div className="anno-layer" onPointerDown={(e) => onPointerDown(e, p)} onPointerMove={(e) => onPointerMove(e, p)} onPointerUp={(e) => onPointerUp(e, p)}>
                      {list.map((it) => it.type === "note" ? (
                        <div key={it.id} className={"anno-note" + (selectedId === it.id ? " sel" : "")} style={{ left: `${it.pos[0] * 100}%`, top: `${it.pos[1] * 100}%` }}
                          onMouseDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); if (mode === "view") { setSelectedId(it.id); editNote(it); } }} title={it.text}>📝</div>
                      ) : (
                        itemRects(it).map((r, k) => (
                          <div key={it.id + "#" + k} className={"anno-item " + it.type + (selectedId === it.id ? " sel" : "")} style={rectStyle(r, it.type, it.color)}
                            onMouseDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); if (mode === "view") setSelectedId(it.id); }} />
                        ))
                      ))}
                      {draft && draft.page === p && <div className={"anno-item " + draft.type + " drafting"} style={rectStyle(draft.box, draft.type, color)} />}
                    </div>
                  </div>
                  <div className="pn">— 第 {p} 页 / 共 {pageCount} 页{list.length ? ` · ${list.length} 条批注` : ""} —</div>
                </div>
              );
            })}
          </div>
        </div>

        {listOpen && (
          <div className="anno-panel">
            <div className="ap-head">
              <b>批注列表</b><span className="ap-count">{items.length}</span>
              <div style={{ flex: 1 }} />
              <button className="btn small" onClick={downloadNotes} disabled={!items.length} title="导出 Markdown">⬇ MD</button>
              <button className="btn small" onClick={copyNotes} disabled={!items.length} title="复制为 Markdown">📄 复制</button>
              <button className="btn small ghost" onClick={() => setListOpen(false)} title="关闭">✕</button>
            </div>
            <div className="ap-body">
              {!items.length && <div className="ap-empty">还没有批注。<br />在正文选中文字，或点工具栏的框选/便签，即可在此汇总、跳转、导出笔记。</div>}
              {Object.entries(items.reduce((acc, it) => { (acc[it.page] = acc[it.page] || []).push(it); return acc; }, {}))
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([pg, its]) => (
                  <div className="ap-page" key={pg}>
                    <div className="ap-page-h">第 {pg} 页 · {its.length}</div>
                    {its.map((it) => (
                      <div key={it.id} className={"ap-item" + (selectedId === it.id ? " sel" : "")}>
                        <button className="ap-item-main" onClick={() => jumpToItem(it)} title="跳转并选中">
                          <span className="ap-ico">{TYPE_ICON[it.type] || "•"}</span>
                          <span className="ap-txt">{it.type === "note" ? (it.text || "（空便签）") : `${TYPE_CN[it.type] || it.type}：${(it.text || "").slice(0, 40) || "（区域）"}`}</span>
                        </button>
                        <button className="ap-del" onClick={() => { setItems((a) => a.filter((x) => x.id !== it.id)); setDirty(true); if (selectedId === it.id) setSelectedId(null); }} title="删除">✕</button>
                      </div>
                    ))}
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {selPopup && (
        <div className="sel-popup" style={{ left: selPopup.left, top: selPopup.top }} onMouseDown={(e) => e.stopPropagation()}>
          <button onClick={() => { setColor(DEFAULT_COLOR.highlight); addFromSelection("highlight"); }}>🖍 高亮</button>
          <button onClick={() => { setColor(DEFAULT_COLOR.underline); addFromSelection("underline"); }}>🟘 下划线</button>
          <button onClick={() => { setColor(DEFAULT_COLOR.strike); addFromSelection("strike"); }}>🚫 删除线</button>
          <button onClick={() => addFromSelection("note")}>📝 便签</button>
        </div>
      )}
    </div>
  );
}
