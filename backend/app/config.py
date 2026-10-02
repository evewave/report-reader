"""全局配置：环境变量 + 可选 .env 文件解析（不引入 python-dotenv 依赖）。

设计约束（贴合个人本机、数据敏感不上云）：
- 默认只绑定 127.0.0.1，服务不出本机局域网。
- 所有 PDF、渲染页图、SQLite 全部落在 backend/data 目录。
- AI 通过 OpenAI 接口调用，API Key 由 .env 或环境变量提供，绝不硬编码。
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- 路径 ----
BACKEND_DIR = Path(__file__).resolve().parent.parent          # .../report-reader/backend
ROOT_DIR = BACKEND_DIR.parent                                  # .../report-reader
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PAGES_DIR = DATA_DIR / "pages"                                 # 逐页渲染的 PNG
EXPORT_DIR = DATA_DIR / "exports"                              # 导出的自包含 HTML
DB_PATH = DATA_DIR / "report-reader.db"
SKILLS_DIR = BACKEND_DIR / "skills"                            # 可插拔 skill 根目录

for _d in (DATA_DIR, UPLOAD_DIR, PAGES_DIR, EXPORT_DIR, SKILLS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析：KEY=VALUE，忽略注释与空行；已存在的真实环境变量优先。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BACKEND_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class Settings:
    # 服务
    HOST: str = _get("RR_HOST", "127.0.0.1")
    PORT: int = int(_get("RR_PORT", "8000") or 8000)

    # OpenAI 接口
    OPENAI_API_KEY: str = _get("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = _get("OPENAI_BASE_URL")  # 可留空用官方；支持中转/兼容网关
    OPENAI_MODEL: str = _get("OPENAI_MODEL", "gpt-4o")
    OPENAI_VISION_MODEL: str = _get("OPENAI_VISION_MODEL", _get("OPENAI_MODEL", "gpt-4o"))
    OPENAI_TEMPERATURE: float = float(_get("OPENAI_TEMPERATURE", "0.2") or 0.2)
    OPENAI_TIMEOUT: float = float(_get("OPENAI_TIMEOUT", "180") or 180)

    # 分析时喂给模型的文本上限（字符），超出会分块再汇总
    MAX_TEXT_CHARS: int = int(_get("RR_MAX_TEXT_CHARS", "60000") or 60000)
    # 逐页渲染分辨率（DPI 越高越清晰，文件越大）
    RENDER_DPI: int = int(_get("RR_RENDER_DPI", "120") or 120)

    @property
    def ai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)


settings = Settings()
