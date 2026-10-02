import React, { useEffect, useRef, useState } from "react";
import { pageImageUrl } from "../api.js";

export default function PdfViewer({ docId, pageCount, jump }) {
  const [zoom, setZoom] = useState(2); // 默认 200%（页面基准宽 760px × zoom）
  const [page, setPage] = useState(1);
  const scrollRef = useRef(null);
  const pageRefs = useRef({});

  useEffect(() => { setPage(1); }, [docId]);

  // 接收来自图表/章节的跳转信号：jump = { page, n }
  useEffect(() => {
    if (!jump || !jump.page) return;
    const el = pageRefs.current[jump.page];
    if (el && scrollRef.current) {
      scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
      el.classList.add("flash");
      setTimeout(() => el.classList.remove("flash"), 1200);
      setPage(jump.page);
    }
  }, [jump]);

  const goTo = (p) => {
    p = Math.min(Math.max(1, p), pageCount);
    const el = pageRefs.current[p];
    if (el && scrollRef.current) scrollRef.current.scrollTo({ top: el.offsetTop - 8, behavior: "smooth" });
    setPage(p);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="pager" style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center" }}>
        <button className="btn small" onClick={() => goTo(page - 1)}>上一页</button>
        <input
          className="btn small" style={{ width: 56, textAlign: "center" }} type="number" min="1" max={pageCount} value={page}
          onChange={(e) => setPage(e.target.value)} onKeyDown={(e) => e.key === "Enter" && goTo(Number(e.target.value))}
        />
        <span>/ {pageCount}</span>
        <button className="btn small" onClick={() => goTo(page + 1)}>下一页</button>
        <span style={{ width: 12 }} />
        <button className="btn small" onClick={() => setZoom((z) => Math.max(0.6, +(z - 0.2).toFixed(1)))}>－</button>
        <span>{Math.round(zoom * 100)}%</span>
        <button className="btn small" onClick={() => setZoom((z) => Math.min(2.4, +(z + 0.2).toFixed(1)))}>＋</button>
      </div>
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "10px 0 40px" }}>
        <div className="pdf-view">
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
            <div
              key={p} className="pdf-page" ref={(el) => (pageRefs.current[p] = el)}
              style={{ width: 760 * zoom, maxWidth: "96%" }}
            >
              <img src={pageImageUrl(docId, p)} loading="lazy" alt={`第 ${p} 页`} />
              <div className="pn">— 第 {p} 页 / 共 {pageCount} 页 —</div>
            </div>
          ))}
        </div>
      </div>
      <style>{`.pdf-page.flash { outline: 3px solid var(--primary); outline-offset: 2px; }`}</style>
    </div>
  );
}
