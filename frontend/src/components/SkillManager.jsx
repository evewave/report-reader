import React, { useEffect, useMemo, useState } from "react";
import { listSkills, getSkill, toggleSkill, installSkill } from "../api.js";

export default function SkillManager({ open, onClose }) {
  const [skills, setSkills] = useState([]);
  const [detail, setDetail] = useState({});
  const [expanded, setExpanded] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = () => listSkills().then(setSkills).catch((e) => setMsg(e.message));
  useEffect(() => { if (open) { refresh(); setMsg(""); } }, [open]);

  const grouped = useMemo(() => {
    const map = {};
    for (const s of skills) {
      const cat = s.category || "其他";
      (map[cat] = map[cat] || []).push(s);
    }
    return map;
  }, [skills]);

  if (!open) return null;

  const showPrompt = async (id) => {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    if (!detail[id]) {
      const s = await getSkill(id).catch(() => null);
      if (s) setDetail((d) => ({ ...d, [id]: s }));
    }
  };

  const onToggle = async (id, enabled) => {
    setBusy(true);
    try { await toggleSkill(id, enabled); refresh(); }
    catch (e) { setMsg(e.message); }
    setBusy(false);
  };

  const onInstall = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setMsg("");
    try {
      const s = await installSkill(file);
      setMsg(`已安装 skill：${s.name}（放文件夹进 backend/skills 也能自动识别）`);
      refresh();
    } catch (err) {
      setMsg("安装失败：" + err.message);
    }
    setBusy(false);
    e.target.value = "";
  };

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="mh">
          <b>技能 / Skills</b>
          <span className="hint" style={{ marginLeft: 10 }}>可插拔：每个分析视角一个 skill</span>
          <button className="btn small close" onClick={onClose}>关闭</button>
        </div>
        <div className="mb">
          <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 10 }}>
            <label className="btn small">
              📦 安装 .zip skill
              <input type="file" accept=".zip" style={{ display: "none" }} onChange={onInstall} />
            </label>
            <span className="hint">zip 内需含 SKILL.md；也可直接把文件夹放进 backend/skills/</span>
            {busy && <span className="spin" />}
          </div>
          {msg && <div className="card" style={{ background: "var(--primary-weak)" }}>{msg}</div>}

          {Object.entries(grouped).map(([cat, list]) => (
            <div key={cat} style={{ marginBottom: 10 }}>
              <div className="cat-head">{cat}<span className="cat-n">{list.length}</span></div>
              {list.map((s) => (
                <div className="skill-row" key={s.id}>
                  <div className="top">
                    <span className="nm">{s.name}</span>
                    <span className="badge">v{s.version}</span>
                    {s.needs_vision && <span className="badge vision">视觉</span>}
                    <label className="switch" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <input type="checkbox" checked={s.enabled} onChange={(e) => onToggle(s.id, e.target.checked)} />
                      <span className="hint">{s.enabled ? "启用" : "停用"}</span>
                    </label>
                  </div>
                  <div className="desc">{s.description}</div>
                  <div className="tags">
                    {(s.report_types || []).map((t) => <span className="badge" key={t}>{t}</span>)}
                    <button className="btn small ghost" onClick={() => showPrompt(s.id)}>
                      {expanded === s.id ? "收起提示词" : "查看提示词"}
                    </button>
                  </div>
                  {expanded === s.id && (
                    <>
                      <div className="hint" style={{ margin: "8px 0 4px" }}>占位符：{s.placeholders?.join(", ") || "（无）"}</div>
                      <pre className="prompt">{detail[s.id]?.prompt_template || "加载中…"}</pre>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))}
          {!skills.length && <div className="empty">未扫描到 skill</div>}
        </div>
      </div>
    </div>
  );
}
