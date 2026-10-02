"""可插拔 Skill 系统。

约定：`backend/skills/<skill_id>/` 一个目录即一个 skill，放入即被扫描识别（无需重启）。
每个 skill 目录：
    SKILL.md     —— YAML frontmatter（id/name/description/version/tags/report_types/needs_vision）
                    + 正文（作为分析时的补充说明 instructions）
    prompt.md    —— 提示词模板（含 {{title}}/{{text}}/{{tables}}/{{pages_json}} 等占位符），
                    若缺失则回退用 SKILL.md 正文
    charts.json  —— 可选，图表偏好/模板提示

启用状态持久化到 SQLite 的 skill_state 表；新发现的 skill 默认启用。
"""
from __future__ import annotations

import io
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .. import database as db
from ..config import SKILLS_DIR

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _parse_frontmatter(md: str) -> tuple[dict[str, str], str]:
    fm: dict[str, str] = {}
    body = md
    if md.lstrip().startswith("---"):
        parts = md.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].lstrip("\n")
    return fm, body


def _split_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_one(folder: Path, enabled_map: dict[str, int]) -> dict[str, Any] | None:
    skill_md = folder / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    fm, body = _parse_frontmatter(text)
    skill_id = folder.name
    prompt_file = folder / "prompt.md"
    prompt_template = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else body
    charts_file = folder / "charts.json"
    chart_hints = charts_file.read_text(encoding="utf-8") if charts_file.exists() else ""

    return {
        "id": skill_id,
        "name": fm.get("name") or skill_id,
        "description": fm.get("description", ""),
        "category": fm.get("category", "其他"),
        "version": fm.get("version", "0.1.0"),
        "author": fm.get("author", ""),
        "tags": _split_list(fm.get("tags", "")),
        "report_types": _split_list(fm.get("report_types", "")),
        "needs_vision": _as_bool(fm.get("needs_vision", "false")),
        "uses_text_model": _as_bool(fm.get("uses_text_model", "true")),
        "enabled": bool(enabled_map.get(skill_id, 1)),
        "placeholders": sorted(set(_PLACEHOLDER_RE.findall(prompt_template))),
        "instructions": body.strip(),
        "prompt_template": prompt_template,
        "chart_hints": chart_hints,
        "path": str(folder),
    }


def _enabled_map() -> dict[str, int]:
    rows = db.query("SELECT skill_id, enabled FROM skill_state")
    return {r["skill_id"]: int(r["enabled"]) for r in rows}


def discover() -> list[dict[str, Any]]:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    enabled_map = _enabled_map()
    skills: list[dict[str, Any]] = []
    for folder in sorted(SKILLS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        meta = _load_one(folder, enabled_map)
        if meta:
            skills.append(meta)
    return skills


def get(skill_id: str) -> dict[str, Any] | None:
    folder = SKILLS_DIR / skill_id
    meta = _load_one(folder, _enabled_map())
    return meta


def set_enabled(skill_id: str, enabled: bool) -> None:
    db.execute(
        """INSERT INTO skill_state(skill_id, enabled, updated_at)
           VALUES(?, ?, datetime('now','localtime'))
           ON CONFLICT(skill_id) DO UPDATE SET enabled=excluded.enabled,
             updated_at=datetime('now','localtime')""",
        (skill_id, 1 if enabled else 0),
    )


def fill_prompt(template: str, values: dict[str, Any]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        val = values.get(key, "")
        return val if isinstance(val, str) else str(val)

    return _PLACEHOLDER_RE.sub(repl, template)


def install_from_zip(data: bytes) -> dict[str, Any]:
    """从 zip 安装 skill。zip 根可包含一个目录（含 SKILL.md），也可直接在根放 SKILL.md。
    安全：拒绝绝对路径与 .. 逃逸；单个 skill；重名则覆盖更新。"""
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("zip 超过 20MB 上限")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        # 找到 SKILL.md 所在目录
        skill_md_member = None
        prefix = ""
        for n in names:
            base = n.rsplit("/", 1)[-1]
            if base == "SKILL.md":
                skill_md_member = n
                prefix = n[: len(n) - len("SKILL.md")]
                break
        if not skill_md_member:
            raise ValueError("zip 内未找到 SKILL.md")

        # 推断 skill_id（目录名，或 zip 文件名回退在调用处处理）
        if prefix:
            skill_id = prefix.rstrip("/").rsplit("/", 1)[-1]
        else:
            skill_id = "imported-skill"
        skill_id = re.sub(r"[^A-Za-z0-9._-]", "-", skill_id).strip("-") or "imported-skill"

        dest = SKILLS_DIR / skill_id
        tmp = SKILLS_DIR / f".tmp_{skill_id}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        for member in zf.infolist():
            rel = member.filename
            if rel.startswith(prefix) and rel[len(prefix):]:
                safe = (rel[len(prefix):]).lstrip("/")
                if ".." in Path(safe).parts:
                    continue  # 拒绝路径逃逸
                target = tmp / safe
                target.parent.mkdir(parents=True, exist_ok=True)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.write_bytes(zf.read(member))
        if not (tmp / "SKILL.md").exists():
            shutil.rmtree(tmp, ignore_errors=True)
            raise ValueError("解压后缺少 SKILL.md")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(tmp), str(dest))

    set_enabled(skill_id, True)
    return get(skill_id) or {"id": skill_id, "name": skill_id, "enabled": True}
