"""OpenAI 兼容接口封装：文本 + 视觉对话，统一要求返回 JSON 并健壮解析。

所有参数（key/base_url/model/温度/超时）来自 settings_store.effective()，
即界面配置优先于 .env。缺 Key 抛 AiNotConfigured（上层转友好提示）。
客户端按 (key, base_url, timeout) 指纹缓存，改配置自动重建。
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from . import settings_store

_client: OpenAI | None = None
_client_fp: tuple | None = None


class AiNotConfigured(RuntimeError):
    pass


_HTML_RE = re.compile(r"<\s*(!doctype|html|head|body)\b", re.I)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def friendly_error(exc: Exception | str) -> str:
    """把异常整理成人话：识别 HTML 响应（多为 Base URL 填错），并做去标签+截断。"""
    msg = str(exc)
    if _HTML_RE.search(msg):
        hint = "接口返回的是网页(HTML)而非 API 的 JSON——Base URL 很可能填错了。"
        m = _TITLE_RE.search(msg)
        if m and m.group(1).strip():
            hint += f" 页面标题：「{m.group(1).strip()[:60]}」。"
        hint += " 正确地址通常是 OpenAI 兼容端点（多以 /v1 结尾，例如 https://api.openai.com/v1）。"
        return hint
    msg = re.sub(r"<[^>]+>", " ", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg[:300] + ("…" if len(msg) > 300 else "")


def _cfg() -> dict[str, Any]:
    return settings_store.effective()


def default_model() -> str:
    return _cfg()["model"]


def default_vision_model() -> str:
    return _cfg()["vision_model"] or _cfg()["model"]


def is_configured() -> bool:
    return bool(_cfg()["api_key"])


def _client_instance() -> OpenAI:
    global _client, _client_fp
    cfg = _cfg()
    if not cfg["api_key"]:
        raise AiNotConfigured(
            "尚未配置 API Key。点击右上角「⚙️ 设置」填入 Key（或配置 backend/.env）。"
        )
    headers = {str(k): str(v) for k, v in (cfg.get("headers") or {}).items() if str(k).strip()}
    fp = (cfg["api_key"], cfg["base_url"], cfg["timeout"], tuple(sorted(headers.items())))
    if _client is None or _client_fp != fp:
        kwargs: dict[str, Any] = {"api_key": cfg["api_key"], "timeout": cfg["timeout"]}
        if cfg["base_url"]:
            kwargs["base_url"] = cfg["base_url"]
        if headers:
            kwargs["default_headers"] = headers
        _client = OpenAI(**kwargs)
        _client_fp = fp
    return _client


def image_data_url(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def chat_text(system: str, user: str, model: str | None = None) -> str:
    client = _client_instance()
    resp = client.chat.completions.create(
        model=model or default_model(),
        temperature=_cfg()["temperature"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


def chat_vision(system: str, user: str, image_paths: list[Path], model: str | None = None) -> str:
    client = _client_instance()
    content: list[dict[str, Any]] = [{"type": "text", "text": user}]
    for p in image_paths:
        if p.exists():
            content.append({"type": "image_url", "image_url": {"url": image_data_url(p)}})
    resp = client.chat.completions.create(
        model=model or default_vision_model(),
        temperature=_cfg()["temperature"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
    )
    return resp.choices[0].message.content or ""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """从模型回复里尽力抠出一个 JSON 对象。"""
    if not text:
        raise ValueError("模型返回为空")
    for cand in _FENCE_RE.findall(text):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            cleaned = re.sub(r",(\s*[}\]])", r"\1", snippet)
            return json.loads(cleaned)
    raise ValueError("无法从模型输出解析 JSON")


def ask_json(system: str, user: str, images: list[Path] | None = None, model: str | None = None) -> dict[str, Any]:
    if images:
        raw = chat_vision(system, user, images, model=model)
    else:
        raw = chat_text(system, user, model=model)
    return extract_json(raw)


def test_connection() -> tuple[bool, str, dict[str, Any]]:
    """用当前生效配置发一条极短消息，验证连通性。返回 (ok, message, info)。"""
    cfg = _cfg()
    if not cfg["api_key"]:
        return False, "未配置 API Key", {"model": cfg["model"]}
    try:
        client = _client_instance()
        resp = client.chat.completions.create(
            model=cfg["model"],
            max_tokens=8,
            messages=[{"role": "user", "content": "ping，只回复 pong"}],
        )
        got = (resp.choices[0].message.content or "").strip()
        return True, f"连接成功：模型返回「{got[:20]}」", {"model": cfg["model"], "reply": got[:40]}
    except Exception as exc:  # noqa: BLE001
        return False, f"连接失败：{friendly_error(exc)}", {"model": cfg["model"]}
