"""运行时 AI 配置：按「厂商档位(provider profiles)」分别保存 base_url / key / 模型 / 请求头，互不混用。

存储结构（data/ai_config.json）：
{
  "active": "opencode-go",              # 当前生效的厂商档位
  "profiles": {
     "opencode-go": {base_url, api_key, model, vision_model, temperature, timeout, headers},
     "deepseek":    {...}, ...
  }
}
- 每个厂商各存各的；切换 active 即整套换用，不会把 A 的 key/模型串到 B。
- 兼容旧的“扁平”结构（顶层直接放 provider/base_url/api_key/...），首次读取自动迁移。
- 优先级：档位值 > .env/环境变量默认。API Key 仅存本机文件，对外 GET 一律打码。
"""
from __future__ import annotations

import json
from typing import Any

from ..config import DATA_DIR, settings

FILE = DATA_DIR / "ai_config.json"

PROFILE_FIELDS = ("base_url", "api_key", "model", "vision_model", "temperature", "timeout", "headers")

PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {"label": "OpenAI 官方", "base_url": "https://api.openai.com/v1", "model": "gpt-4o"},
    "custom": {"label": "自定义/兼容网关", "base_url": "", "model": ""},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "moonshot": {"label": "Moonshot Kimi", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-128k"},
    "dashscope": {"label": "阿里通义(DashScope 兼容)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "zhipu": {"label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-plus"},
    "opencode-go": {"label": "OpenCode Go（需会话头）", "base_url": "https://opencode.ai/zen/go/v1", "model": "mimo-v2.5-pro"},
    "opencode-zen": {"label": "OpenCode Zen（按量付费）", "base_url": "https://opencode.ai/zen/v1", "model": "qwen3.8-max"},
}

_PROFILE_KEYS = set(PROVIDERS.keys())


def _env_defaults() -> dict[str, Any]:
    return {
        "base_url": settings.OPENAI_BASE_URL or "",
        "api_key": settings.OPENAI_API_KEY or "",
        "model": settings.OPENAI_MODEL,
        "vision_model": settings.OPENAI_VISION_MODEL,
        "temperature": settings.OPENAI_TEMPERATURE,
        "timeout": settings.OPENAI_TIMEOUT,
        "headers": {},
    }


def _coerce_profile(p: dict[str, Any]) -> dict[str, Any]:
    out = {k: p.get(k) for k in PROFILE_FIELDS if k in p}
    if "temperature" in out:
        try: out["temperature"] = float(out["temperature"])
        except (TypeError, ValueError): out["temperature"] = 0.2
    if "timeout" in out:
        try: out["timeout"] = float(out["timeout"])
        except (TypeError, ValueError): out["timeout"] = 180.0
    if "headers" in out and not isinstance(out["headers"], dict):
        out["headers"] = {}
    return out


def _load() -> dict[str, Any]:
    """读取并归一为 {active, profiles}；含旧扁平结构自动迁移。"""
    if not FILE.exists():
        return {"active": "", "profiles": {}}
    try:
        raw = json.loads(FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"active": "", "profiles": {}}
    if not isinstance(raw, dict):
        return {"active": "", "profiles": {}}
    if "profiles" in raw and isinstance(raw["profiles"], dict):
        profiles = {k: _coerce_profile(v) for k, v in raw["profiles"].items() if isinstance(v, dict)}
        active = raw.get("active") or _pick_default_active(profiles)
        return {"active": active, "profiles": profiles}
    # —— 旧扁平结构迁移 ——
    prov = (raw.get("provider") or "").strip() or "custom"
    flat = {k: raw[k] for k in PROFILE_FIELDS if k in raw and raw[k] not in (None, "")}
    return {"active": prov, "profiles": {prov: _coerce_profile(flat)}}


def _pick_default_active(profiles: dict[str, dict]) -> str:
    for pid in profiles:  # 选一个有 key 的档位作为默认生效
        if (profiles[pid].get("api_key") or "").strip():
            return pid
    return next(iter(profiles), "")


def _write(active: str, profiles: dict[str, dict[str, Any]]) -> None:
    FILE.write_text(json.dumps({"active": active, "profiles": profiles}, ensure_ascii=False, indent=2), encoding="utf-8")


def effective() -> dict[str, Any]:
    """当前生效档位，字段按 档位值 > .env 默认 兜底。"""
    data = _load()
    pid = data["active"]
    prof = data["profiles"].get(pid, {})
    env = _env_defaults()
    eff = {"provider": pid}
    for k in PROFILE_FIELDS:
        v = prof.get(k)
        if v in (None, "", {}):
            v = env.get(k, "" if k != "headers" else {})
        eff[k] = v
    eff["headers"] = dict(eff.get("headers") or {})
    return eff


def is_configured() -> bool:
    return bool(effective().get("api_key"))


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'·' * 6}{key[-4:]}"


def _mask_profile(p: dict[str, Any]) -> dict[str, Any]:
    key = str(p.get("api_key") or "")
    return {
        "base_url": p.get("base_url", ""),
        "model": p.get("model", ""),
        "vision_model": p.get("vision_model", ""),
        "temperature": p.get("temperature", ""),
        "timeout": p.get("timeout", ""),
        "headers": dict(p.get("headers") or {}),
        "has_key": bool(key.strip()),
        "api_key_masked": mask_key(key),
    }


def masked_view() -> dict[str, Any]:
    data = _load()
    env = _env_defaults()
    profiles = {pid: _mask_profile(p) for pid, p in data["profiles"].items()}
    eff = effective()
    return {
        "active": data["active"],
        "providers": [{"id": k, **v} for k, v in PROVIDERS.items()],
        "profiles": profiles,
        "preset_defaults": {k: {"base_url": v["base_url"], "model": v["model"]} for k, v in PROVIDERS.items()},
        "env_has_key": bool(env["api_key"]),
        "active_eff": {
            "provider": eff["provider"],
            "label": PROVIDERS.get(eff["provider"], {}).get("label", eff["provider"]),
            "base_url": eff["base_url"],
            "model": eff["model"],
            "vision_model": eff["vision_model"] or eff["model"],
            "has_key": bool(eff["api_key"]),
            "api_key_masked": mask_key(eff["api_key"]),
        },
    }


def save_provider(pid: str, fields: dict[str, Any], set_active: bool = False) -> dict[str, Any]:
    data = _load()
    profiles = data["profiles"]
    prof = dict(profiles.get(pid, {}))
    for k in PROFILE_FIELDS:
        if k not in fields:
            continue
        v = fields[k]
        if v is None:                       # None 表示“本次不修改该字段”，一律跳过
            continue
        if k == "api_key":
            prof["api_key"] = str(v).strip()  # 空串=清除；有值=覆盖
        elif k == "headers":
            if isinstance(v, dict):
                prof["headers"] = {str(a).strip(): str(b).strip() for a, b in v.items() if str(a).strip()}
            else:
                prof["headers"] = {}
        elif k in ("temperature", "timeout"):
            try:
                prof[k] = float(v)
            except (TypeError, ValueError):
                pass
        else:
            prof[k] = str(v).strip()
    profiles[pid] = prof
    active = pid if (set_active or not data["active"]) else data["active"]
    _write(active, profiles)
    return masked_view()


def set_active(pid: str) -> dict[str, Any]:
    data = _load()
    if pid not in data["profiles"]:
        raise ValueError("该厂商尚未保存配置，无法启用")
    _write(pid, data["profiles"])
    return masked_view()


def clear_key(pid: str) -> dict[str, Any]:
    data = _load()
    if pid in data["profiles"]:
        data["profiles"][pid].pop("api_key", None)
        _write(data["active"], data["profiles"])
    return masked_view()
