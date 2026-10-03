"""文档相关 API：上传解析、列表、详情、原 PDF 与逐页图取用、可恢复删除。"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import database as db
from ..config import PAGES_DIR, UPLOAD_DIR
from ..services import annotation_service, pdf_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_SUFFIX = {".pdf"}


class AnnotationsRequest(BaseModel):
    items: list[dict[str, Any]] = []


def _get_doc(doc_id: str) -> dict:
    row = db.query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not row:
        raise HTTPException(404, "文档不存在")
    return row


@router.post("")
async def upload_document(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        raise HTTPException(400, "目前仅支持 PDF 文件")

    doc_id = f"d_{uuid.uuid4().hex[:12]}"
    pdf_path = UPLOAD_DIR / f"{doc_id}.pdf"
    try:
        with pdf_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except OSError as exc:
        raise HTTPException(500, f"保存失败：{exc}") from exc

    try:
        extract = pdf_service.parse_pdf(pdf_path, doc_id)
    except Exception as exc:  # noqa: BLE001
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(422, f"PDF 解析失败：{exc}") from exc

    # 落盘完整抽取结果（含逐页文本与表格），DB 仅存轻量 meta
    (UPLOAD_DIR / f"{doc_id}.json").write_text(
        json.dumps(extract, ensure_ascii=False), encoding="utf-8"
    )
    meta = {
        "page_sizes": extract.get("page_sizes", []),
        "page_image_counts": extract.get("page_image_counts", []),
        "pdf_meta": extract.get("meta", {}),
        "filename": file.filename,
    }
    db.execute(
        """INSERT INTO documents(id,title,filename,path,page_count,text_len,table_count,meta_json)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            doc_id, extract["title"], file.filename or f"{doc_id}.pdf", str(pdf_path),
            extract["page_count"], extract["text_len"], extract["table_count"],
            json.dumps(meta, ensure_ascii=False),
        ),
    )
    return {"id": doc_id, "title": extract["title"], "page_count": extract["page_count"],
            "table_count": extract["table_count"], "text_len": extract["text_len"]}


@router.get("")
def list_documents() -> list[dict]:
    rows = db.query(
        """SELECT d.id, d.title, d.filename, d.page_count, d.text_len, d.table_count, d.created_at,
                  (SELECT COUNT(*) FROM analyses a WHERE a.doc_id = d.id) AS analysis_count
           FROM documents d ORDER BY d.created_at DESC"""
    )
    return rows


@router.get("/{doc_id}")
def get_document(doc_id: str) -> dict:
    row = _get_doc(doc_id)
    extract_path = UPLOAD_DIR / f"{doc_id}.json"
    page_texts: list[dict] = []
    tables: list[dict] = []
    if extract_path.exists():
        extract = json.loads(extract_path.read_text(encoding="utf-8"))
        page_texts = [{"page": p["page"], "chars": p["chars"]} for p in extract["pages"]]
        tables = extract.get("tables", [])
    analyses = db.query(
        "SELECT id, skill_id, model, status, summary, created_at, updated_at FROM analyses WHERE doc_id=? ORDER BY updated_at DESC",
        (doc_id,),
    )
    return {
        "id": row["id"], "title": row["title"], "filename": row["filename"],
        "page_count": row["page_count"], "text_len": row["text_len"], "table_count": row["table_count"],
        "created_at": row["created_at"], "meta": row["meta_json"],
        "pages": page_texts, "tables": tables, "analyses": analyses,
    }


@router.get("/{doc_id}/pdf")
def get_pdf(doc_id: str) -> FileResponse:
    row = _get_doc(doc_id)
    p = Path(row["path"])
    if not p.exists():
        raise HTTPException(404, "原始 PDF 文件缺失")
    return FileResponse(p, media_type="application/pdf", filename=row["filename"])


@router.get("/{doc_id}/textlayer")
def get_textlayer(doc_id: str) -> dict[str, Any]:
    row = _get_doc(doc_id)
    p = Path(row["path"])
    if not p.exists():
        raise HTTPException(404, "原始 PDF 文件缺失")
    try:
        return {"pages": pdf_service.text_layer(p)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"文本层生成失败：{pdf_service.__name__} {exc}") from exc


@router.get("/{doc_id}/pages/{page_num}.png")
def get_page_png(doc_id: str, page_num: int) -> FileResponse:
    _get_doc(doc_id)
    img = PAGES_DIR / doc_id / f"page_{page_num:04d}.png"
    if not img.exists():
        raise HTTPException(404, "该页渲染图不存在")
    return FileResponse(img, media_type="image/png")


@router.get("/{doc_id}/annotations")
def get_annotations(doc_id: str) -> dict[str, Any]:
    _get_doc(doc_id)
    return {"items": annotation_service.get_items(doc_id)}


@router.put("/{doc_id}/annotations")
def put_annotations(doc_id: str, body: AnnotationsRequest) -> dict[str, Any]:
    _get_doc(doc_id)
    return annotation_service.save_items(doc_id, body.items)


@router.delete("/{doc_id}/annotations")
def delete_annotations(doc_id: str) -> dict[str, Any]:
    _get_doc(doc_id)
    annotation_service.clear(doc_id)
    return {"cleared": doc_id}


@router.get("/{doc_id}/annotated/pdf")
def get_annotated_pdf(doc_id: str) -> FileResponse:
    row = _get_doc(doc_id)
    p = annotation_service.annotated_path(doc_id)
    if not p:
        raise HTTPException(404, "尚无批注版（先添加批注并保存）")
    name = Path(row["filename"]).stem + "-批注版.pdf"
    return FileResponse(p, media_type="application/pdf", filename=name)


@router.delete("/{doc_id}")
def delete_document(doc_id: str) -> dict:
    _get_doc(doc_id)
    # 可恢复删除：移动到 data/.trash 而非永久删除
    trash = UPLOAD_DIR.parent / ".trash" / f"{int(time.time())}_{doc_id}"
    trash.mkdir(parents=True, exist_ok=True)
    annotation_service.remove_doc_artifacts(doc_id, trash)
    for src in (UPLOAD_DIR / f"{doc_id}.pdf", UPLOAD_DIR / f"{doc_id}.json", PAGES_DIR / doc_id):
        if src.exists():
            shutil.move(str(src), str(trash / src.name))
    db.execute("DELETE FROM analyses WHERE doc_id = ?", (doc_id,))
    db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return {"deleted": doc_id, "recovered_path": str(trash)}
