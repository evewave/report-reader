# Report Reader — AI Research Report Reading Assistant

Turn sell-side research reports, papers, and earnings releases (PDF) into an **interactive HTML reading view**. It extracts text and data tables, converts key numbers into interactive charts (ECharts), and keeps the **original PDF readable page by page** — charts can jump back to their source page. Front-end/back-end separated, fully local-first, your data never leaves your machine.

[![Release](https://img.shields.io/github/v/tag/evewave/report-reader?label=release&sort=semver)](https://github.com/evewave/report-reader/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24%2B-2E7D32?logo=adobeacrobatreader&logoColor=white)](https://pymupdf.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 中文说明: [README.zh-CN.md](README.zh-CN.md)

## Highlights

- **Parse on upload**: per-page text, bordered tables (PyMuPDF `find_tables`), embedded-image stats, and high-res page PNGs — all stored locally.
- **AI analysis**: skill-driven reading that produces a summary, key-metric cards, key points, section map, interactive charts, data tables, risks, and follow-up questions.
- **Interactive charts**: extracted numeric series become ECharts (line / bar / area / pie / scatter / radar, dual-axis supported). Click "go to page N" to highlight the source page in the original PDF.
- **Original PDF reader**: defaults to **200% zoom**, with paging, zoom and page jump; synced with charts. The library sidebar can be collapsed, and peeks out when you hover the left edge.
- **Focus mode**: one click hides the top bar / toolbar clutter and collapses the sidebar so content gets the space (`Esc` to exit).
- **Multi-provider AI config (in-app)**: OpenAI / DeepSeek / Moonshot / DashScope / Zhipu / OpenCode, etc. **Each provider keeps its own key, model and headers — no cross-contamination.** Custom request headers supported (e.g. OpenCode Go's `x-opencode-session`).
- **Pluggable skills**: one folder = one skill. Drop it into `backend/skills/` and it is auto-discovered. Enable/disable, inspect prompts, or install via `.zip` from the UI.
- **Export standalone HTML**: export an analysis as a **single-file, offline-openable/shareable** HTML with inlined ECharts and interactive charts.
- **Light/dark theme**, **analysis history**, and **recoverable delete** (files move to `data/.trash`).

## Tech Stack

React 18 + Vite (front-end) / FastAPI + SQLite + PyMuPDF + openai SDK (back-end).

## Project Layout

```
report-reader/
├── backend/
│   ├── run.py                 # entry: python run.py → http://127.0.0.1:8000
│   ├── requirements.txt
│   ├── .env.example           # optionally copy to .env (in-app config also works)
│   ├── app/
│   │   ├── config.py          # settings & paths (binds 127.0.0.1 by default)
│   │   ├── database.py        # SQLite (documents / analyses / skill_state)
│   │   ├── main.py            # FastAPI app + CORS + serves front-end dist
│   │   ├── routers/           # documents / analyze / skills / settings
│   │   └── services/          # pdf_service / ai_service / skill_loader / analysis_pipeline / export_service / settings_store
│   ├── skills/                # ★ pluggable skills (14 built-in, 6 categories)
│   └── data/                  # runtime data: uploads, page PNGs, SQLite, AI config (auto-created, git-ignored)
├── frontend/
│   ├── src/                   # App + api + components (PdfViewer / AnalysisView / ChartCard / SkillManager / SettingsModal / UploadDrop)
│   └── vite.config.js         # dev proxy /api → backend
├── start.bat                  # dev mode: run backend + frontend together
└── serve.bat                  # single port: build front-end, serve everything from backend
```

## Requirements

- Python 3.10+ (verified on 3.12), Node 18+ (verified on v24).
- Backend: `pip install -r backend/requirements.txt`
- Frontend: `cd frontend && npm install`

## Quick Start

### 1) Configure AI (optional)
- **Recommended**: after launching, open **⚙️ Settings** in the top-right and fill the key/model under the provider tab you want. It is stored locally in `backend/data/ai_config.json` and **masked** when read back.
- Or copy `backend/.env.example` to `backend/.env` and set `OPENAI_API_KEY` (in-app config takes precedence over `.env`).

> No key? You can still upload, extract, read the original PDF page by page, and export. Only "Analyze" needs AI.

### 2) Run

Single port (simplest) — double-click `serve.bat`, or:
```bash
cd frontend && npm install && npm run build
cd ../backend && python run.py      # open http://127.0.0.1:8000
```

Dev mode (front-end hot reload) — double-click `start.bat`, or:
```bash
# terminal A
cd backend && python run.py                       # http://127.0.0.1:8000
# terminal B
cd frontend && npm run dev                        # http://127.0.0.1:5173 (proxies /api)
```

> If the port is busy, set `RR_PORT=8100`; in dev mode also set `RR_BACKEND=http://127.0.0.1:8100` so Vite proxies to it.

## Workflow

1. Drag & drop (or pick) PDFs in the left sidebar — multiple files supported.
2. Choose a skill (grouped by category) at the top; tick "Vision refine" if your model supports images.
3. Click **▶ Analyze** → the **AI Reading** tab shows summary, metric cards, interactive charts, sections, tables, risks and questions.
4. Click "go to page N" on a chart to jump to the source page in the **Original PDF** tab; view/delete past runs under **History**.
5. Use 🧘 **Focus** for a clean reading layout, and **📤 Export HTML** to share an offline, self-contained page.

## Skills (Pluggable)

**14 built-in skills across 6 categories:**

| Category | Skills |
| --- | --- |
| Stocks & Companies | `stock-deep`, `earnings-flash`, `quant-fundamental` |
| Industry & Allocation | `industry-research`, `quant-portfolio`, `industry-rotation` |
| Quant & Financial Engineering | `quant-strategy-eval`, `quant-factor`, `quant-ml`, `event-arbitrage` |
| Risk & Fixed Income | `quant-risk`, `bond-cb` |
| Crypto | `crypto-research` |
| Academic | `academic-paper` |

**Adding a skill** = create a folder under `backend/skills/` (add/rename/remove takes effect without restarting; reopen the Skills dialog to refresh the list):

```
skills/my-skill/
├── SKILL.md     # YAML frontmatter + body (body is used as the instructions)
└── prompt.md    # prompt template with placeholders; falls back to SKILL.md body if absent
```

`SKILL.md` frontmatter fields:

| Field | Description |
| --- | --- |
| `name` | Display name |
| `category` | Grouping used by the UI (dropdown/panel); defaults to "Other" |
| `description` | Short description |
| `version` / `author` / `tags` | Metadata (`tags` comma-separated) |
| `report_types` | Applicable report types (comma-separated) |
| `needs_vision` | `true/false`, default hint for vision refine |
| `uses_text_model` | defaults to `true` |

`prompt.md` placeholders (filled automatically): `{{title}}`, `{{n_pages}}`, `{{text}}` (per-page text, truncated if long), `{{tables}}` (extracted tables), `{{pages_json}}`, `{{instructions}}`, `{{chart_hints}}`.

The model is asked to return one strict JSON object (summary / metrics / key points / sections / figures / tables / risks / questions); the backend `_normalize_result` cleans and validates numbers, and the front-end renders it. **Every skill shares the same contract, so new skills need no front-end changes.** You can also install a skill via `.zip` (a folder containing `SKILL.md`) in the Skills dialog.

## Export Standalone HTML

Click **📤 Export HTML** in the "AI Reading" header to generate a **single self-contained** HTML file (the local `echarts.min.js` is inlined, so it works fully offline; falls back to CDN if the file is missing). Text, metrics and tables are server-rendered (readable and printable without JS); charts stay interactive.

## API Reference (`/api`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health`, `/ai/status` | Health and effective AI config |
| POST | `/documents` | Upload & parse a PDF (multipart `file`) |
| GET | `/documents`, `/documents/{id}` | List / detail (pages, tables) |
| GET | `/documents/{id}/pdf`, `/pages/{n}.png` | Original PDF / page image |
| DELETE | `/documents/{id}` | Delete (moves files to `data/.trash`, recoverable) |
| POST | `/analyze` | Run analysis (`{doc_id, skill_id, use_vision}`) |
| GET | `/analyses/{id}`, `/documents/{id}/analyses` | Fetch result / list |
| GET | `/analyses/{id}/export` | Export standalone HTML (`?inline=1` to view in browser) |
| GET/POST | `/skills`, `/skills/{id}/toggle`, `/skills/install` | List / toggle / install skills |
| GET/POST | `/settings/ai`, `/settings/ai/active`, `/settings/ai/test`, `/settings/ai/key` | AI config: read / save a provider profile / activate / test / clear key |

## Privacy & Security

- Binds only to `127.0.0.1` by default. Uploaded PDFs, page images, SQLite and AI config live in `backend/data/`, which is **git-ignored and never committed**.
- API keys are stored locally only (`data/ai_config.json` per-provider profile, or `.env`) and are **masked** on read. **No key is present anywhere in the source code.**
- Only the "Analyze" step sends report text / chart pages to the AI endpoint you configured. Everything else is local.

## FAQ

- **429 / 401 on analyze**: invalid key or exhausted quota. Switch provider profile/key in **Settings**, or set `OPENAI_BASE_URL` to a working gateway.
- **OpenCode Go returns `MissingSessionID`**: it requires a header — add `x-opencode-session: <session-string>` to that provider's custom headers in Settings.
- **Tables not detected**: `find_tables` relies on ruled borders; borderless layouts are read from the text instead — you may also enable "Vision refine".
- **Changes under `backend/skills/` don't appear**: reopen the Skills dialog to re-scan.
- **Front-end changes not visible**: hard refresh with `Ctrl+F5`; for production re-run `npm run build`.
- **Static assets 404 after rebuild**: restart the backend (StaticFiles caches the mounted directory).

## License

MIT — see [LICENSE](LICENSE).
