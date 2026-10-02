"""AI 分析 API。"""
from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .. import database as db
from ..config import settings
from ..services import ai_service, analysis_pipeline, export_service, settings_store

router = APIRouter(prefix="/api", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    doc_id: str
    skill_id: str
    use_vision: bool | None = None


def _serialize(analysis_row: dict) -> dict[str, Any]:
    result = analysis_row["result_json"] if isinstance(analysis_row["result_json"], dict) else {}
    return {
        "id": analysis_row["id"],
        "doc_id": analysis_row["doc_id"],
        "skill_id": analysis_row["skill_id"],
        "model": analysis_row["model"],
        "status": analysis_row["status"],
        "summary": analysis_row["summary"],
        "error": analysis_row.get("error", ""),
        "created_at": analysis_row["created_at"],
        "updated_at": analysis_row["updated_at"],
        "result": result,
    }


@router.get("/ai/status")
def ai_status() -> dict[str, Any]:
    eff = settings_store.effective()
    return {
        "configured": bool(eff["api_key"]),
        "provider": eff["provider"],
        "model": eff["model"],
        "vision_model": eff["vision_model"] or eff["model"],
        "base_url": eff["base_url"] or "https://api.openai.com/v1",
    }


@router.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict[str, Any]:
    doc = db.query_one("SELECT id, title FROM documents WHERE id = ?", (req.doc_id,))
    if not doc:
        raise HTTPException(404, "文档不存在")

    analysis_id = f"a_{uuid.uuid4().hex[:12]}"
    try:
        result = analysis_pipeline.run_analysis(req.doc_id, req.skill_id, req.use_vision)
    except ai_service.AiNotConfigured as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        brief = ai_service.friendly_error(exc)
        db.execute(
            """INSERT INTO analyses(id,doc_id,skill_id,model,status,summary,result_json,error)
               VALUES(?,?,?,?, 'error', '', '{}', ?)""",
            (analysis_id, req.doc_id, req.skill_id, settings.OPENAI_MODEL, brief),
        )
        raise HTTPException(502, f"分析失败：{brief}") from exc

    db.execute(
        """INSERT INTO analyses(id,doc_id,skill_id,model,status,summary,result_json,error)
           VALUES(?,?,?,?, 'done', ?, ?, '')""",
        (
            analysis_id, req.doc_id, req.skill_id, result["meta"].get("model", settings.OPENAI_MODEL),
            result.get("summary", "")[:500], json.dumps(result, ensure_ascii=False),
        ),
    )
    row = db.query_one("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    return _serialize(row)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str) -> dict[str, Any]:
    row = db.query_one("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    if not row:
        raise HTTPException(404, "分析结果不存在")
    return _serialize(row)


@router.get("/analyses/{analysis_id}/export")
def export_analysis(analysis_id: str, inline: bool = Query(False, description="1=浏览器内查看；默认下载")) -> HTMLResponse:
    row = db.query_one("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    if not row:
        raise HTTPException(404, "分析结果不存在")
    if row["status"] != "done":
        raise HTTPException(400, "该分析未完成，无法导出")
    result = row["result_json"] if isinstance(row["result_json"], dict) else {}
    if not result:
        raise HTTPException(400, "分析结果为空，无法导出")
    html_text = export_service.build_html(result)
    fname = export_service.safe_filename(result.get("meta", {}).get("title") or row["skill_id"])
    disposition = "inline" if inline else "attachment"
    headers = {
        "Content-Disposition": f"{disposition}; filename=\"report.html\"; filename*=UTF-8''{quote(fname)}"
    }
    return HTMLResponse(content=html_text, headers=headers)


@router.get("/documents/{doc_id}/analyses")
def list_analyses(doc_id: str) -> list[dict[str, Any]]:
    rows = db.query(
        "SELECT * FROM analyses WHERE doc_id=? ORDER BY updated_at DESC", (doc_id,)
    )
    return [_serialize(r) for r in rows]


@router.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: str) -> dict[str, str]:
    row = db.query_one("SELECT id FROM analyses WHERE id = ?", (analysis_id,))
    if not row:
        raise HTTPException(404, "分析结果不存在")
    db.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    return {"deleted": analysis_id}
