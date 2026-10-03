"""PDF 批注：批注项按文档持久化（SQLite），并烘焙成一份独立的「批注版 PDF」。

- 原始 PDF 文件（uploads/{id}.pdf）永不修改；批注版写到 annotated/{id}.pdf。
- 批注项用「归一化坐标」[0..1]，随缩放无关；烘焙时用原始页物理尺寸(pt)换算为 PDF 坐标。
- 支持类型：highlight / underline / strike / rect（框）用矩形 box=[x0,y0,x1,y1]；note 用 pos=[x,y] + text。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pymupdf as fitz

from .. import database as db
from ..config import ANNOTATED_DIR, UPLOAD_DIR


def get_items(doc_id: str) -> list[dict[str, Any]]:
    row = db.query_one("SELECT items_json FROM annotations WHERE doc_id = ?", (doc_id,))
    if not row:
        return []
    data = row["items_json"]
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = []
    return data if isinstance(data, list) else []


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    s = (value or "").lstrip("#")
    if len(s) != 6:
        return (1.0, 0.87, 0.0)  # 默认黄
    try:
        return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (1.0, 0.87, 0.0)


def _norm_box(item: dict[str, Any], w: float, h: float, pad: float = 0.0) -> fitz.Rect | None:
    box = item.get("box")
    if not (isinstance(box, list) and len(box) == 4):
        return None
    x0, y0, x1, y1 = box
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    r = fitz.Rect(x0 * w, y0 * h, x1 * w, y1 * h)
    if pad:
        r = fitz.Rect(r.x0 - pad, r.y0 - pad, r.x1 + pad, r.y1 + pad)
    return r if r.width > 0 and r.height > 0 else r  # 允许极扁（下划线/删除线用线状）


def _apply(doc_id: str, items: list[dict[str, Any]]) -> Path | None:
    row = db.query_one("SELECT path, meta_json FROM documents WHERE id = ?", (doc_id,))
    out = ANNOTATED_DIR / f"{doc_id}.pdf"
    if not row or not items:
        out.unlink(missing_ok=True)
        return None
    src = Path(row["path"])
    if not src.exists():
        src = UPLOAD_DIR / f"{doc_id}.pdf"
    if not src.exists():
        out.unlink(missing_ok=True)
        return None
    meta = row["meta_json"] if isinstance(row["meta_json"], dict) else {}
    sizes = {p["page"]: (p["w"], p["h"]) for p in meta.get("page_sizes", []) if isinstance(p, dict) and p.get("page")}

    with fitz.open(src) as pdf:
        for it in items:
            pno = it.get("page")
            if not isinstance(pno, int) or pno < 1 or pno > pdf.page_count:
                continue
            page = pdf[pno - 1]
            w, h = sizes.get(pno, (page.rect.width, page.rect.height))
            color = _hex_to_rgb(it.get("color", ""))
            kind = it.get("type")
            try:
                if kind == "note":
                    pos = it.get("pos")
                    if not (isinstance(pos, list) and len(pos) == 2):
                        continue
                    pt = fitz.Point(pos[0] * w, pos[1] * h)
                    annot = page.add_text_annot(pt, str(it.get("text", "")))
                    annot.set_info(title="批注", content=str(it.get("text", "")))
                    annot.set_colors(stroke=color)
                elif kind in ("highlight", "underline", "strike", "rect"):
                    boxes = it.get("rects")
                    if not (isinstance(boxes, list) and boxes and isinstance(boxes[0], list)):
                        b = it.get("box")
                        boxes = [b] if (isinstance(b, list) and len(b) == 4) else []
                    for rb in boxes:
                        rect = _norm_box({"box": rb}, w, h, pad=0.5)
                        if not rect:
                            continue
                        if kind == "highlight":
                            annot = page.add_highlight_annot(rect)
                            annot.set_colors(stroke=color)
                            annot.set_opacity(0.4)
                        elif kind == "underline":
                            annot = page.add_underline_annot(rect)
                            annot.set_colors(stroke=color)
                        elif kind == "strike":
                            annot = page.add_strikeout_annot(rect)
                            annot.set_colors(stroke=color)
                        else:  # rect 框
                            annot = page.add_rect_annot(rect)
                            annot.set_colors(stroke=color)
                            annot.set_border(width=1.5)
                        annot.update()
                    continue
            except Exception:  # noqa: BLE001 - 单项失败不影响整体
                continue
        ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
        pdf.save(out, deflate=True)
    return out


def save_items(doc_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    items = items if isinstance(items, list) else []
    db.execute(
        """INSERT INTO annotations(doc_id, items_json, updated_at)
           VALUES(?,?, datetime('now','localtime'))
           ON CONFLICT(doc_id) DO UPDATE SET items_json=excluded.items_json, updated_at=excluded.updated_at""",
        (doc_id, json.dumps(items, ensure_ascii=False)),
    )
    out = _apply(doc_id, items)
    return {"count": len(items), "annotated_exists": bool(out and out.exists())}


def clear(doc_id: str) -> None:
    db.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
    (ANNOTATED_DIR / f"{doc_id}.pdf").unlink(missing_ok=True)


def remove_doc_artifacts(doc_id: str, trash: Path) -> None:
    """删除文档时，把批注版 PDF 一并移入回收目录（可恢复）。"""
    f = ANNOTATED_DIR / f"{doc_id}.pdf"
    if f.exists():
        db.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
        trash.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(trash / f.name))


def annotated_path(doc_id: str) -> Path | None:
    p = ANNOTATED_DIR / f"{doc_id}.pdf"
    return p if p.exists() else None
