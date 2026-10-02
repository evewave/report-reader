import React, { useRef, useState } from "react";
import { uploadDocument } from "../api.js";

export default function UploadDrop({ onUploaded, onError }) {
  const [over, setOver] = useState(false);
  const [prog, setProg] = useState(null);
  const inputRef = useRef(null);

  const handleFiles = async (files) => {
    const list = Array.from(files || []).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!list.length) { onError && onError("请选择 PDF 文件"); return; }
    for (let i = 0; i < list.length; i++) {
      setProg(0);
      try {
        const res = await uploadDocument(list[i], (p) => setProg(Math.round(p * 100)));
        onUploaded && onUploaded(res);
      } catch (e) {
        onError && onError(`《${list[i].name}》导入失败：${e.message}`);
      }
    }
    setProg(null);
  };

  return (
    <div
      className={"drop" + (over ? " over" : "")}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); handleFiles(e.dataTransfer.files); }}
      onClick={() => inputRef.current?.click()}
    >
      <div className="big">＋ 拖拽或点击上传研报 PDF</div>
      <div className="hint">支持多选；数据仅存本机 backend/data</div>
      {prog !== null && (
        <div className="progress"><i style={{ width: prog + "%" }} /></div>
      )}
      <input ref={inputRef} type="file" accept="application/pdf,.pdf" multiple style={{ display: "none" }}
        onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} />
    </div>
  );
}
