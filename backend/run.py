"""后端启动入口：python run.py → http://127.0.0.1:8000

- 自动打开 SQLite、扫描 skills 目录。
- reload=True 便于开发；如需生产可改成 RR_NO_RELOAD=1 或关掉 reload。
"""
from __future__ import annotations

import os

import uvicorn

from app.config import settings


def main() -> None:
    reload = os.environ.get("RR_NO_RELOAD", "") != "1"
    print(f"[report-reader] 后端启动：http://{settings.HOST}:{settings.PORT}")
    print(f"[report-reader] AI: {'已配置 ' + settings.OPENAI_MODEL if settings.ai_configured else '未配置 OPENAI_API_KEY（分析功能不可用，浏览/阅读仍可用）'}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=reload)


if __name__ == "__main__":
    main()
