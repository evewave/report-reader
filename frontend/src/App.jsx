import React, { useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api.js";
import UploadDrop from "./components/UploadDrop.jsx";
import PdfViewer from "./components/PdfViewer.jsx";
import AnalysisView from "./components/AnalysisView.jsx";
import SkillManager from "./components/SkillManager.jsx";
import SettingsModal from "./components/SettingsModal.jsx";

function initialTheme() {
  try {
    const s = localStorage.getItem("rr-theme");
    if (s === "light" || s === "dark") return s;
  } catch (_) { /* ignore */ }
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null); // doc 摘要
  const [detail, setDetail] = useState(null); // doc 详情
  const [skills, setSkills] = useState([]);
  const [ai, setAi] = useState({ configured: false, model: "" });

  const [theme, setTheme] = useState(initialTheme);
  const [showSettings, setShowSettings] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try { return localStorage.getItem("rr-sidebar") !== "0"; } catch (_) { return true; }
  });
  const [topbarHidden, setTopbarHidden] = useState(() => {
    try { return localStorage.getItem("rr-topbar") === "0"; } catch (_) { return false; }
  });

  const [skillId, setSkillId] = useState("");
  const [useVision, setUseVision] = useState(false);
  const [tab, setTab] = useState("ai");
  const [jump, setJump] = useState(null);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [analyses, setAnalyses] = useState([]);

  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");
  const [showSkills, setShowSkills] = useState(false);

  const enabledSkills = useMemo(() => skills.filter((s) => s.enabled), [skills]);

  const skillsByCategory = useMemo(() => {
    const map = {};
    for (const s of enabledSkills) {
      const cat = s.category || "其他";
      (map[cat] = map[cat] || []).push(s);
    }
    return map;
  }, [enabledSkills]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("rr-theme", theme); } catch (_) { /* ignore */ }
  }, [theme]);

  useEffect(() => {
    try { localStorage.setItem("rr-sidebar", sidebarOpen ? "1" : "0"); } catch (_) { /* ignore */ }
  }, [sidebarOpen]);

  useEffect(() => {
    try { localStorage.setItem("rr-topbar", topbarHidden ? "0" : "1"); } catch (_) { /* ignore */ }
  }, [topbarHidden]);

  const [peeking, setPeeking] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [headerPeek, setHeaderPeek] = useState(false);
  const focusBefore = useRef(true);

  const enterFocus = () => { focusBefore.current = sidebarOpen; setSidebarOpen(false); setHeaderPeek(false); setFocusMode(true); };
  const exitFocus = () => { setFocusMode(false); setHeaderPeek(false); setSidebarOpen(focusBefore.current); };
  const toggleFocus = () => (focusMode ? exitFocus() : enterFocus());

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape" && focusMode) exitFocus(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusMode]);

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(""), 6000); };

  const loadDocs = () => api.listDocuments().then(setDocs).catch((e) => flash(e.message));
  const loadSkills = () => api.listSkills().then(setSkills).catch((e) => flash(e.message));
  const loadAi = () => api.aiStatus().then(setAi).catch(() => setAi({ configured: false }));

  useEffect(() => {
    loadAi();
    loadDocs();
    loadSkills();
  }, []);

  // 默认选中第一个启用 skill
  useEffect(() => {
    if (!skillId && enabledSkills.length) {
      setSkillId(enabledSkills[0].id);
      setUseVision(enabledSkills[0].needs_vision);
    }
  }, [enabledSkills, skillId]);

  const selectDoc = async (id) => {
    setSelected(id);
    setTab("ai");
    setActiveAnalysis(null);
    const d = await api.getDocument(id).catch((e) => { flash(e.message); return null; });
    setDetail(d);
    const list = await api.listAnalyses(id).catch(() => []);
    setAnalyses(list);
    const done = list.find((a) => a.status === "done");
    if (done) setActiveAnalysis(done);
  };

  const onUploaded = async (res) => {
    await loadDocs();
    flash(`已导入《${res.title}》`);
    selectDoc(res.id);
  };

  const onDeleteDoc = async (id, e) => {
    e.stopPropagation();
    if (!confirm("删除该研报？文件会移到回收目录，可手动恢复。")) return;
    await api.deleteDocument(id).catch((err) => flash(err.message));
    if (selected === id) { setSelected(null); setDetail(null); setActiveAnalysis(null); }
    loadDocs();
  };

  const runAnalyze = async () => {
    if (!selected) return;
    if (!ai.configured) { flash("尚未配置 OPENAI_API_KEY，无法运行 AI 分析"); return; }
    setRunning(true);
    try {
      const res = await api.analyze(selected, skillId, useVision);
      setActiveAnalysis(res);
      setTab("ai");
      const list = await api.listAnalyses(selected).catch(() => []);
      setAnalyses(list);
      flash("分析完成");
    } catch (e) {
      flash("分析失败：" + e.message);
    }
    setRunning(false);
  };

  const openHistory = async (a) => {
    const full = await api.getAnalysis(a.id).catch((e) => { flash(e.message); return null; });
    if (full) { setActiveAnalysis(full); setTab("ai"); setTabKey((k) => k + 1); }
  };

  // 让 AnalysisView 在重复打开同一分析时也能刷新（可选）
  const [tabKey, setTabKey] = useState(0);

  const onDeleteAnalysis = async (id) => {
    await api.deleteAnalysis(id).catch((e) => flash(e.message));
    const list = await api.listAnalyses(selected).catch(() => []);
    setAnalyses(list);
    if (activeAnalysis?.id === id) setActiveAnalysis(null);
  };

  const onJump = (page) => { setTab("pdf"); setJump({ page, n: Date.now() }); };

  return (
    <div className="app">
      {(topbarHidden || focusMode) && <div className="top-hover" onMouseEnter={() => setHeaderPeek(true)} />}
      <div
        className={"topbar" + ((topbarHidden || focusMode) ? " collapsed" : "") + (headerPeek ? " peek" : "")}
        onMouseLeave={() => { if (topbarHidden || focusMode) setHeaderPeek(false); }}
      >
        {focusMode ? (
          <>
            <span className="focus-title" title={detail?.title || ""}>{detail?.title || "专注阅读"}</span>
            <div className="spacer" />
            <button className="btn small ghost focus-exit" onClick={exitFocus} title="退出专注（Esc）">✕ Esc</button>
          </>
        ) : (
          <>
            <button className="btn icon" onClick={() => setTopbarHidden((v) => !v)} title={topbarHidden ? "固定顶栏" : "隐藏顶栏（鼠标移到顶部可唤回）"}>
              {topbarHidden ? "⤓" : "⤒"}
            </button>
            <button className="btn icon" onClick={() => setSidebarOpen((v) => !v)} title={sidebarOpen ? "收起资料库侧栏" : "展开资料库侧栏"}>
              {sidebarOpen ? "«" : "»"}
            </button>
            <div className="brand">
              <span className="logo">◈</span>
              研报 AI 阅读助手<span className="sub">上传 PDF → AI 解析 → 可交互图表阅读</span>
            </div>
            <div className="spacer" />
            <button className={"chip " + (ai.configured ? "ok" : "warn")} onClick={() => setShowSettings(true)} title="点击配置 AI 接口">
              <span className="dot" />
              {ai.configured ? `AI 就绪 · ${ai.model}` : "未配置 · 点我设置"}
            </button>
            <button className="btn icon" onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))} title="切换深浅色">
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <button className="btn" onClick={() => setShowSkills(true)}>🧩 Skills（{enabledSkills.length}/{skills.length}）</button>
            <button className="btn" onClick={() => setShowSettings(true)}>⚙️ 设置</button>
            <button className="btn" onClick={toggleFocus} title="专注阅读：隐藏杂乱入口并放大阅读区">🧘 专注</button>
          </>
        )}
      </div>

      <div className="body">
        {!sidebarOpen && !peeking && (
          <div className="sidebar-peek-handle" onMouseEnter={() => setPeeking(true)} onClick={() => setSidebarOpen(true)} title="悬停或点击展开资料库">»</div>
        )}
        <aside
          className={"sidebar" + (sidebarOpen ? "" : " collapsed") + (peeking ? " peeking" : "")}
          onMouseLeave={() => { if (!sidebarOpen) setPeeking(false); }}
        >
          <div className="head">
            <span>资料库（{docs.length}）</span>
            <button className="btn small ghost head-collapse" onClick={() => setSidebarOpen(false)} title="收起侧栏">«</button>
          </div>
          <div className="scroll">
            <UploadDrop onUploaded={onUploaded} onError={flash} />
            {docs.map((d) => (
              <div key={d.id} className={"doclist-item" + (selected === d.id ? " active" : "")} onClick={() => selectDoc(d.id)}>
                <div className="t">{d.title}</div>
                <div className="m">
                  <span>{d.page_count} 页</span>
                  <span>{d.table_count} 表</span>
                  {d.analysis_count > 0 && <span>· {d.analysis_count} 份分析</span>}
                  <button className="del" onClick={(e) => onDeleteDoc(d.id, e)}>删除</button>
                </div>
              </div>
            ))}
            {!docs.length && <div className="hint" style={{ textAlign: "center", padding: 20 }}>还没有研报，先上传 PDF</div>}
          </div>
        </aside>

        <main className="main">
          {detail && (
            <div className={"toolbar" + (focusMode ? " focus" : "")}>
              <div className="title" title={detail.title}>{detail.title}</div>
              <span className="meta">{detail.page_count} 页 · {detail.text_len.toLocaleString()} 字 · {detail.table_count} 表</span>
              <div className="spacer" style={{ flex: 1 }} />
              <select value={skillId} onChange={(e) => {
                setSkillId(e.target.value);
                const s = skills.find((x) => x.id === e.target.value);
                if (s) setUseVision(s.needs_vision);
              }}>
                {Object.entries(skillsByCategory).map(([cat, list]) => (
                  <optgroup key={cat} label={cat}>
                    {list.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </optgroup>
                ))}
                {!enabledSkills.length && <option value="">（无启用 skill）</option>}
              </select>
              <label className="chip" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={useVision} onChange={(e) => setUseVision(e.target.checked)} /> 视觉校正图表
              </label>
              <button className="btn primary" onClick={runAnalyze} disabled={running || !skillId}>
                {running ? <><span className="spin" /> 分析中…</> : "▶ 开始分析"}
              </button>
              <div className="tabs">
                <button className={tab === "ai" ? "active" : ""} onClick={() => setTab("ai")}>AI 精读</button>
                <button className={tab === "pdf" ? "active" : ""} onClick={() => setTab("pdf")}>原 PDF</button>
                <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>分析记录({analyses.length})</button>
              </div>
            </div>
          )}
          {msg && <div className="card" style={{ background: "var(--primary-weak)", margin: "10px 16px 0" }}>{msg}</div>}

          {!detail ? (
            <div className="content">
              <div className="empty">
                <div className="big">📑</div>
                <div>从左侧上传研报 / 论文 PDF，选择技能后开始 AI 分析</div>
                <div className="hint" style={{ marginTop: 8 }}>即使暂不配置 API，也能浏览与逐页阅读已导入的 PDF</div>
              </div>
            </div>
          ) : tab === "pdf" ? (
            <div style={{ flex: 1, minHeight: 0 }}>
              <PdfViewer docId={detail.id} pageCount={detail.page_count} jump={jump} docTitle={detail.title} focusMode={focusMode} />
            </div>
          ) : tab === "history" ? (
            <div className="content">
              {analyses.length ? analyses.map((a) => (
                <div className="card" key={a.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{a.skill_id} · {a.model}</div>
                    <div className="hint">{a.created_at} · 状态 {a.status}</div>
                    <div style={{ marginTop: 4 }}>{a.summary?.slice(0, 120) || "（无概述）"}</div>
                  </div>
                  <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                    <button className="btn small" onClick={() => openHistory(a)} disabled={a.status !== "done"}>查看</button>
                    <button className="btn small" onClick={() => onDeleteAnalysis(a.id)}>删除</button>
                  </div>
                </div>
              )) : <div className="empty">暂无分析记录</div>}
            </div>
          ) : (
            <div className="content">
              {activeAnalysis ? (
                <AnalysisView key={activeAnalysis.id + "-" + tabKey} analysis={activeAnalysis} onJump={onJump} />
              ) : (
                <div className="empty">
                  <div className="big">✨</div>
                  <div>点击右上「开始分析」，AI 会抽取正文与图表数据，生成可交互阅读视图</div>
                  <div className="hint" style={{ marginTop: 8 }}>可选技能决定分析侧重；勾选「视觉校正」让 AI 读图更准</div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      <SkillManager open={showSkills} onClose={() => setShowSkills(false)} />
      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} onSaved={loadAi} />
      {running && (
        <div className="loading-overlay">
          <div className="box">
            <div className="spin" style={{ width: 26, height: 26, borderWidth: 3 }} />
            <div style={{ marginTop: 10 }}>AI 正在解析研报…</div>
            <div className="hint">长文与视觉识别可能需要数十秒</div>
          </div>
        </div>
      )}
    </div>
  );
}
