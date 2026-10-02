import React, { useEffect, useMemo, useState } from "react";
import { getAiSettings, saveAiSettings, setActiveProvider, testAiSettings, clearAiKey } from "../api.js";

function parseHeaders(text) {
  const obj = {};
  (text || "").split(/\r?\n/).forEach((line) => {
    const t = line.trim();
    if (!t || t.startsWith("#")) return;
    const i = t.indexOf(":");
    if (i <= 0) return;
    const k = t.slice(0, i).trim();
    const v = t.slice(i + 1).trim();
    if (k) obj[k] = v;
  });
  return obj;
}
const headersToText = (h) => Object.entries(h || {}).map(([k, v]) => `${k}: ${v}`).join("\n");

const EMPTY_FORM = { base_url: "", api_key: "", model: "", vision_model: "", temperature: 0.2, timeout: 180, headersText: "" };

export default function SettingsModal({ open, onClose, onSaved }) {
  const [data, setData] = useState({ providers: [], profiles: {}, preset_defaults: {}, active: "" });
  const [selected, setSelected] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const providers = data.providers || [];
  const profiles = data.profiles || {};
  const presets = data.preset_defaults || {};

  const selectedPreset = presets[selected] || {};
  const selectedProfile = profiles[selected];

  function loadProfile(pid, d) {
    const p = (d.profiles || {})[pid];
    const seed = (d.preset_defaults || {})[pid] || {};
    setForm({
      base_url: p?.base_url ?? seed.base_url ?? "",
      api_key: "",
      model: p?.model ?? seed.model ?? "",
      vision_model: p?.vision_model ?? "",
      temperature: p?.temperature ?? 0.2,
      timeout: p?.timeout ?? 180,
      headersText: headersToText(p?.headers),
    });
  }

  async function refresh(keepSelected) {
    const d = await getAiSettings();
    setData(d);
    const sel = keepSelected && d.active ? keepSelected : d.active || (d.providers?.[0]?.id ?? "");
    setSelected(sel);
    loadProfile(sel, d);
    return d;
  }

  useEffect(() => {
    if (!open) return;
    setFeedback(null);
    refresh().catch((e) => setFeedback({ ok: false, msg: e.message }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const pickProvider = (pid) => {
    setSelected(pid);
    loadProfile(pid, data);
    setFeedback(null);
  };

  if (!open) return null;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const buildPayload = () => {
    const payload = {
      base_url: form.base_url,
      model: form.model,
      vision_model: form.vision_model,
      temperature: Number(form.temperature),
      timeout: Number(form.timeout),
      headers: parseHeaders(form.headersText),
    };
    if (form.api_key.trim()) payload.api_key = form.api_key.trim();
    return payload;
  };

  const doSave = async (setActive) => {
    if (!selected) return;
    setBusy(true); setFeedback(null);
    try {
      await saveAiSettings(selected, buildPayload(), setActive);
      await refresh(selected);
      setFeedback({ ok: true, msg: setActive ? `已保存到「${labelOf(selected)}」并设为当前使用` : `已保存到「${labelOf(selected)}」` });
      onSaved && onSaved();
    } catch (e) { setFeedback({ ok: false, msg: "保存失败：" + e.message }); }
    setBusy(false);
  };

  const doActivate = async () => {
    setBusy(true); setFeedback(null);
    try { await setActiveProvider(selected); await refresh(selected); setFeedback({ ok: true, msg: `当前使用已切换为「${labelOf(selected)}」` }); onSaved && onSaved(); }
    catch (e) { setFeedback({ ok: false, msg: e.message }); }
    setBusy(false);
  };

  const doTest = async () => {
    if (!selected) return;
    setTesting(true); setFeedback(null);
    try {
      await saveAiSettings(selected, buildPayload(), true);   // 先存并设为当前，确保测的是界面上这套
      await refresh(selected);
      const r = await testAiSettings();
      setFeedback({ ok: r.ok, msg: r.message });
      onSaved && onSaved();
    } catch (e) { setFeedback({ ok: false, msg: "测试失败：" + e.message }); }
    setTesting(false);
  };

  const doClearKey = async () => {
    setBusy(true);
    try { await clearAiKey(selected); await refresh(selected); setFeedback({ ok: true, msg: "已清除该厂商的 Key" }); onSaved && onSaved(); }
    catch (e) { setFeedback({ ok: false, msg: e.message }); }
    setBusy(false);
  };

  const labelOf = (pid) => providers.find((p) => p.id === pid)?.label || pid;
  const isActive = (pid) => data.active === pid;

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal settings" onClick={(e) => e.stopPropagation()}>
        <div className="mh">
          <b>⚙️ AI 接口设置</b>
          <span className="pill">当前使用：{data.active ? `${labelOf(data.active)}` : "未设置"}</span>
          <button className="btn close" onClick={onClose}>完成</button>
        </div>
        <div className="mb">
          <div className="field">
            <label>厂商档位（各存各的 key/模型，互不混用）</label>
            <div className="prov-tabs">
              {providers.map((p) => (
                <button key={p.id} className={"prov-tab" + (selected === p.id ? " on" : "") + (isActive(p.id) ? " active" : "")}
                  onClick={() => pickProvider(p.id)}>
                  <span className="pt-name">{p.label}</span>
                  {isActive(p.id) && <span className="pt-star" title="当前使用">★</span>}
                  {(profiles[p.id]?.has_key) && <span className="pt-dot" title="已存 Key" />}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Base URL</label>
            <input value={form.base_url} onChange={(e) => set("base_url", e.target.value)} placeholder="https://api.openai.com/v1" />
            {form.base_url && !/^https?:\/\//i.test(form.base_url) && <div className="tip" style={{ color: "var(--danger)" }}>需以 http:// 或 https:// 开头</div>}
            {form.base_url && /^https?:\/\//i.test(form.base_url) && !/\/v\d+(\/.*)?$/i.test(form.base_url) && (
              <div className="tip" style={{ color: "var(--warn)" }}>OpenAI 兼容接口通常以 /v1 结尾。留空则用官方默认。</div>
            )}
          </div>

          <div className="field">
            <label>API Key <span className="muted-inline">（仅存本机、返回打码，切换厂商互不覆盖）</span></label>
            <div className="row">
              <input type="password" value={form.api_key} onChange={(e) => set("api_key", e.target.value)}
                placeholder={selectedProfile?.has_key ? `已保存 ${selectedProfile.api_key_masked}（留空则不修改）` : "粘贴该厂商的 API Key"} autoComplete="off" />
              {selectedProfile?.has_key && <button className="btn" onClick={doClearKey} disabled={busy}>清除</button>}
            </div>
          </div>

          <div className="grid2">
            <div className="field"><label>文本模型</label><input value={form.model} onChange={(e) => set("model", e.target.value)} placeholder={selectedPreset.model || "gpt-4o"} /></div>
            <div className="field"><label>视觉模型（可留空）</label><input value={form.vision_model} onChange={(e) => set("vision_model", e.target.value)} placeholder="留空复用文本模型" /></div>
          </div>

          <div className="grid2">
            <div className="field"><label>Temperature（{form.temperature}）</label><input type="range" min="0" max="1" step="0.1" value={form.temperature} onChange={(e) => set("temperature", e.target.value)} /></div>
            <div className="field"><label>超时（秒）</label><input type="number" min="10" step="10" value={form.timeout} onChange={(e) => set("timeout", e.target.value)} /></div>
          </div>

          <div className="field">
            <label>自定义请求头（可选，每行 Key: Value）</label>
            <textarea value={form.headersText} onChange={(e) => set("headersText", e.target.value)}
              placeholder={"x-opencode-session: my-session-001"} rows={2}
              style={{ width: "100%", height: "auto", padding: "8px 10px", resize: "vertical", lineHeight: 1.5 }} />
            <div className="tip">OpenCode Go 需填 <code>x-opencode-session: 固定串</code>；一般厂商留空。</div>
          </div>

          {feedback && <div className={"feedback " + (feedback.ok ? "ok" : "err")} title={feedback.msg}>{feedback.ok ? "✅ " : "⚠️ "}{feedback.msg.length > 300 ? feedback.msg.slice(0, 300) + "…" : feedback.msg}</div>}
        </div>
        <div className="mf">
          <button className="btn" onClick={doTest} disabled={testing || busy}>{testing ? <><span className="spin" /> 测试中</> : "🔌 测试连接"}</button>
          <button className="btn" onClick={doActivate} disabled={busy || !profiles[selected]} style={{ opacity: profiles[selected] ? 1 : 0.5 }}>★ 设为当前使用</button>
          <div className="spacer" style={{ flex: 1 }} />
          <button className="btn primary" onClick={() => doSave(isActive(selected))} disabled={busy || !selected || !form.model}>💾 保存</button>
        </div>
      </div>
    </div>
  );
}
