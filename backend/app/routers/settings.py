"""AI 配置 API：按厂商档位分别保存 base_url/key/模型/请求头，互不混用。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import ai_service, settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AiProfileRequest(BaseModel):
    provider: str                          # 目标厂商档位
    set_active: bool = False               # 保存后是否设为当前生效
    base_url: str | None = None
    api_key: str | None = None             # None=不改；""=清除；有值=覆盖
    model: str | None = None
    vision_model: str | None = None
    temperature: float | None = None
    timeout: float | None = None
    headers: dict[str, str] | None = None  # 自定义请求头，如 {"x-opencode-session": "..."}


@router.get("/ai")
def get_ai() -> dict[str, Any]:
    return settings_store.masked_view()


@router.post("/ai")
def save_ai(body: AiProfileRequest) -> dict[str, Any]:
    pid = body.provider.strip()
    if not pid:
        raise HTTPException(400, "provider 不能为空")
    fields = {k: v for k, v in body.model_dump().items() if k in settings_store.PROFILE_FIELDS and v is not None}
    try:
        return settings_store.save_provider(pid, fields, set_active=body.set_active)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"保存失败：{settings_store.__name__} {ai_service.friendly_error(exc)}") from exc


class ActiveRequest(BaseModel):
    provider: str


@router.post("/ai/active")
def set_active(body: ActiveRequest) -> dict[str, Any]:
    try:
        return settings_store.set_active(body.provider.strip())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class KeyAction(BaseModel):
    provider: str
    action: str  # clear


@router.post("/ai/key")
def key_action(body: KeyAction) -> dict[str, Any]:
    if body.action == "clear":
        return settings_store.clear_key(body.provider.strip())
    return settings_store.masked_view()


@router.post("/ai/test")
def test_ai() -> dict[str, Any]:
    ok, message, info = ai_service.test_connection()
    return {"ok": ok, "message": message, "info": info}
