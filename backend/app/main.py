"""FastAPI 应用装配：CORS（放行 Vite dev）、启动建库、路由挂载、可选前端静态托管。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import database as db
from .config import settings
from .routers import analyze, documents, settings as settings_router, skills
from .services import ai_service

app = FastAPI(title="Report Reader 后端", version="1.0.0",
              description="研报 AI 阅读助手：上传 PDF → 抽取 → AI 分析 → 可交互 HTML 阅读")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173", "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"ok": True, "ai_configured": ai_service.is_configured(),
            "model": ai_service.default_model(), "host": settings.HOST, "port": settings.PORT}


app.include_router(documents.router)
app.include_router(analyze.router)
app.include_router(skills.router)
app.include_router(settings_router.router)

# 生产模式：若已构建前端 dist，则一并托管，单命令即可访问整站
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
