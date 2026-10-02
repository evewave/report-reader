"""Skill 管理 API：列表、详情、启用/禁用、zip 安装。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..services import skill_loader

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _brief(skill: dict) -> dict[str, Any]:
    """列表用的轻量视图（不含 prompt 正文，减少体积）。"""
    return {
        "id": skill["id"], "name": skill["name"], "description": skill["description"],
        "category": skill.get("category", "其他"),
        "version": skill["version"], "author": skill["author"], "tags": skill["tags"],
        "report_types": skill["report_types"], "needs_vision": skill["needs_vision"],
        "uses_text_model": skill["uses_text_model"], "enabled": skill["enabled"],
        "placeholders": skill["placeholders"],
    }


@router.get("")
def list_skills() -> list[dict[str, Any]]:
    return [_brief(s) for s in skill_loader.discover()]


@router.get("/{skill_id}")
def get_skill(skill_id: str) -> dict[str, Any]:
    skill = skill_loader.get(skill_id)
    if not skill:
        raise HTTPException(404, "skill 不存在")
    return skill


class ToggleRequest(BaseModel):
    enabled: bool


@router.post("/{skill_id}/toggle")
def toggle(skill_id: str, body: ToggleRequest) -> dict[str, Any]:
    if not skill_loader.get(skill_id):
        raise HTTPException(404, "skill 不存在")
    skill_loader.set_enabled(skill_id, body.enabled)
    return _brief(skill_loader.get(skill_id))


@router.post("/install")
async def install(file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    try:
        skill = skill_loader.install_from_zip(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"安装失败：{exc}") from exc
    return _brief(skill)
