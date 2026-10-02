"""PDF 解析：文本、表格、内嵌图统计、逐页渲染 PNG。全部基于 PyMuPDF(fitz)。"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pymupdf as fitz  # 新版 PyMuPDF 推荐导入名（fitz 为旧别名，已弃用）

from ..config import PAGES_DIR, settings


def doc_id_for(path: Path, originalname: str) -> str:
    """稳定短 id：文件名 + 大小 + 内容首块哈希，避免同路径重复导入互相覆盖。"""
    stat = path.stat()
    h = hashlib.sha1()
    h.update(originalname.encode("utf-8"))
    h.update(str(stat.st_size).encode())
    with path.open("rb") as f:
        h.update(f.read(65536))
    return f"d_{h.hexdigest()[:12]}"


def _clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_with_pages(doc: fitz.Document) -> list[dict[str, Any]]:
    """逐页文本，带页码（1 基），用于 AI 上下文与阅读锚点。"""
    pages: list[dict[str, Any]] = []
    for i, page in enumerate(doc):
        txt = _clean_text(page.get_text("text"))
        pages.append({"page": i + 1, "text": txt, "chars": len(txt)})
    return pages


def extract_tables(doc: fitz.Document) -> list[dict[str, Any]]:
    """逐页 find_tables，返回结构化表格（含页码）。"""
    tables: list[dict[str, Any]] = []
    for i, page in enumerate(doc):
        try:
            found = page.find_tables()
        except Exception:  # noqa: BLE001 - 某些版式解析失败直接跳过
            continue
        for t in getattr(found, "tables", []):
            try:
                data = t.extract()
            except Exception:  # noqa: BLE001
                continue
            rows = [[("" if c is None else str(c).strip()) for c in row] for row in data]
            rows = [r for r in rows if any(cell for cell in r)]
            if len(rows) >= 2:
                tables.append({"page": i + 1, "rows": rows, "n_rows": len(rows), "n_cols": max(len(r) for r in rows)})
    return tables


def count_page_images(doc: fitz.Document) -> list[int]:
    """每页内嵌位图数量，用于判断哪些页可能是图表页（供视觉模型二次识别）。"""
    counts: list[int] = []
    for page in doc:
        try:
            counts.append(len(page.get_images(full=True)))
        except Exception:  # noqa: BLE001
            counts.append(0)
    return counts


def render_pages(doc: fitz.Document, out_dir: Path, dpi: int | None = None) -> int:
    """把每一页渲染成 PNG，供前端逐页阅读与视觉模型识别。返回页数。"""
    dpi = dpi or settings.RENDER_DPI
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(out_dir / f"page_{i + 1:04d}.png")
    return doc.page_count


def parse_pdf(pdf_path: Path, doc_id: str) -> dict[str, Any]:
    """总入口：打开 PDF，产出文本/表格/图统计 + 落盘逐页 PNG。"""
    with fitz.open(pdf_path) as doc:
        meta = doc.metadata or {}
        title_guess = (meta.get("title") or "").strip()
        pages = extract_text_with_pages(doc)
        tables = extract_tables(doc)
        img_counts = count_page_images(doc)
        page_dir = PAGES_DIR / doc_id
        rendered = render_pages(doc, page_dir)
        page_sizes = []
        for page in doc:
            r = page.rect
            page_sizes.append({"page": int(page.number) + 1, "w": round(r.width, 1), "h": round(r.height, 1)})

    total_text = "\n".join(p["text"] for p in pages)
    # 标题猜测：PDF 元数据 > 首页第一行非空 > 文件名
    if not title_guess:
        for p in pages[:2]:
            for line in p["text"].splitlines():
                if len(line.strip()) >= 4:
                    title_guess = line.strip()
                    break
            if title_guess:
                break

    return {
        "doc_id": doc_id,
        "title": title_guess or pdf_path.stem,
        "page_count": rendered,
        "text_len": len(total_text),
        "table_count": len(tables),
        "pages": pages,
        "tables": tables,
        "page_image_counts": img_counts,
        "page_sizes": page_sizes,
        "meta": {k: v for k, v in meta.items() if v},
    }
