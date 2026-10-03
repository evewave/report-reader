// 与后端 FastAPI 交互的统一封装。全部使用同源 /api 前缀：
// - dev：vite.config.js 把 /api 代理到 127.0.0.1:8000
// - prod：FastAPI 直接托管 dist，仍是同源
const BASE = "/api";

async function json(path, options = {}) {
  const resp = await fetch(BASE + path, options);
  const ct = resp.headers.get("content-type") || "";
  if (!resp.ok) {
    let msg = `请求失败 ${resp.status}`;
    try {
      const data = ct.includes("json") ? await resp.json() : await resp.text();
      msg = (data && data.detail) || data || msg;
    } catch (_) {
      /* ignore */
    }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return ct.includes("json") ? resp.json() : resp.text();
}

// ---- AI 状态 ----
export const aiStatus = () => json("/ai/status");

// ---- AI 配置（按厂商档位分别保存，互不混用）----
export const getAiSettings = () => json("/settings/ai");
export const saveAiSettings = (provider, fields, setActive = false) =>
  json("/settings/ai", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ provider, set_active: setActive, ...fields }),
  });
export const setActiveProvider = (provider) =>
  json("/settings/ai/active", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ provider }),
  });
export const clearAiKey = (provider) =>
  json("/settings/ai/key", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ provider, action: "clear" }),
  });
export const testAiSettings = () =>
  json("/settings/ai/test", { method: "POST" });

// ---- 文档 ----
export const listDocuments = () => json("/documents");
export const getDocument = (id) => json(`/documents/${id}`);
export const deleteDocument = (id) => json(`/documents/${id}`, { method: "DELETE" });

export function uploadDocument(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", BASE + "/documents");
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        let msg = `上传失败 ${xhr.status}`;
        try {
          msg = JSON.parse(xhr.responseText).detail || msg;
        } catch (_) {
          /* ignore */
        }
        reject(new Error(msg));
      }
    };
    xhr.onerror = () => reject(new Error("网络错误，上传失败"));
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

export const pageImageUrl = (docId, page) => `${BASE}/documents/${docId}/pages/${page}.png`;
export const pdfUrl = (docId) => `${BASE}/documents/${docId}/pdf`;
export const annotatedPdfUrl = (docId) => `${BASE}/documents/${docId}/annotated/pdf`;

// ---- PDF 批注 ----
export const getAnnotations = (docId) => json(`/documents/${docId}/annotations`);
export const getTextLayer = (docId) => json(`/documents/${docId}/textlayer`);
export const saveAnnotations = (docId, items) =>
  json(`/documents/${docId}/annotations`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ items }),
  });
export const deleteAnnotations = (docId) => json(`/documents/${docId}/annotations`, { method: "DELETE" });

// ---- 分析 ----
export const analyze = (docId, skillId, useVision) =>
  json("/analyze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ doc_id: docId, skill_id: skillId, use_vision: useVision }),
  });
export const listAnalyses = (docId) => json(`/documents/${docId}/analyses`);
export const getAnalysis = (id) => json(`/analyses/${id}`);
export const deleteAnalysis = (id) => json(`/analyses/${id}`, { method: "DELETE" });

// ---- Skills ----
export const listSkills = () => json("/skills");
export const getSkill = (id) => json(`/skills/${id}`);
export const toggleSkill = (id, enabled) =>
  json(`/skills/${id}/toggle`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
export function installSkill(file) {
  const fd = new FormData();
  fd.append("file", file);
  return json("/skills/install", { method: "POST", body: fd });
}
