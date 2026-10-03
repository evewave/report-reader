# 研报 AI 阅读助手（report-reader）

把券商研报 / 论文 / 业绩公告等 PDF，交给 AI 分析后转成**可交互的 HTML 阅读视图**：自动抽取正文与数据表格、把关键数据生成可交互图表（ECharts），同时**保留原 PDF 逐页阅读**，图表可一键定位回原文页。前后端分离、纯本机运行、数据不出本机。

[![Release](https://img.shields.io/github/v/release/evewave/report-reader?label=release)](https://github.com/evewave/report-reader/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24%2B-2E7D32?logo=adobeacrobatreader&logoColor=white)](https://pymupdf.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> English README: [README.md](README.md)

## 核心能力

- **上传即解析**：逐页文本、带边框表格（PyMuPDF `find_tables`）、每页内嵌图统计、逐页渲染高清 PNG，全部落本机。
- **AI 分析**：按「技能」侧重解析，产出总览、关键指标卡、核心要点、章节导览、数据图表、数据表、风险、待追问问题。
- **可交互图表**：抽取的数值序列渲染为 ECharts（折线/柱状/面积/饼/散点/雷达，支持双轴），点「定位第 N 页」跳回原 PDF 对应页并高亮。
- **原 PDF 逐页阅读**：默认 200% 放大、翻页/缩放/页码跳转，与图表联动；侧栏可收起，鼠标移到左边缘自动浮出。
- **PDF 批注**：高亮 / 下划线 / 删除线 / 框选 / 便签。**选中正文即弹出批注菜单**（支持多行、捕获所选文字），或在图表上拖框。批注按文档持久化，并烘焙成**独立的批注版 PDF**（原始文件永不改动）；批注列表侧栏按页汇总、点击跳转、可**导出/复制 Markdown 笔记**。
- **专注阅读模式**：一键隐去顶栏/工具栏杂项、自动收起侧栏，把版面让给内容（`Esc` 退出）；专注下仍可靠「选中文本」批注。顶栏也可单独隐藏（鼠标移到顶部滑出）。
- **多厂商 AI 配置（界面内）**：OpenAI / DeepSeek / Kimi / 通义 / 智谱 / OpenCode 等，**每个厂商各存各的 Key/模型/请求头，互不混用**；支持自定义请求头（如 OpenCode Go 的 `x-opencode-session`）。
- **可插拔 Skills**：一个文件夹 = 一个技能，放入 `backend/skills/` 即自动识别；界面可启用/禁用、查看提示词、`.zip` 安装。
- **导出独立 HTML**：把分析结果导出为**单文件、离线可打开/分享**的 HTML（内联 ECharts，图表可交互）。
- **深浅色主题**、**分析记录**、**可恢复删除**（文件移入 `data/.trash`）。

## 技术栈

React 18 + Vite（前端） / FastAPI + SQLite + PyMuPDF + openai SDK（后端）。

## 目录结构

```
report-reader/
├── backend/
│   ├── run.py                 # 入口：python run.py → http://127.0.0.1:8000
│   ├── requirements.txt
│   ├── .env.example           # 可复制为 .env（界面里配置也行）
│   ├── app/
│   │   ├── config.py          # 配置与路径（默认只绑 127.0.0.1）
│   │   ├── database.py        # SQLite（documents / analyses / skill_state）
│   │   ├── main.py            # FastAPI 装配 + CORS + 托管前端 dist
│   │   ├── routers/           # documents / analyze / skills / settings
│   │   └── services/          # pdf_service / ai_service / skill_loader / analysis_pipeline / export_service / settings_store
│   ├── skills/                # ★ 可插拔技能目录（内置 14 个，分 6 类）
│   └── data/                  # 运行时数据：上传 PDF、逐页 PNG、SQLite、AI 配置（自动创建，已 gitignore）
├── frontend/
│   ├── src/                   # App + api + 组件（PdfViewer / AnalysisView / ChartCard / SkillManager / SettingsModal / UploadDrop）
│   └── vite.config.js         # dev 把 /api 代理到后端
├── start.bat                  # 开发模式：同时起后端 + 前端
└── serve.bat                  # 单端口：构建后由后端托管整站
```

## 环境要求

- Python 3.10+（已在 3.12 验证），Node 18+（已在 v24 验证）。
- 后端依赖：`pip install -r backend/requirements.txt`
- 前端依赖：`cd frontend && npm install`

## 快速开始

### 1) 配置 AI（可选）
- **推荐**：启动后点界面右上角「⚙️ 设置」，在厂商分档里填 Key/模型（存本机 `backend/data/ai_config.json`，返回时打码）。
- 或复制 `backend/.env.example` 为 `backend/.env` 填 `OPENAI_API_KEY`（界面配置优先于 `.env`）。

> 不配 Key 也能用：上传、抽取、原 PDF 逐页阅读、导出都可用；仅「开始分析」需要 AI。

### 2) 启动

单端口（最省事）——双击 `serve.bat`，或：
```bash
cd frontend && npm install && npm run build
cd ../backend && python run.py      # 打开 http://127.0.0.1:8000
```

开发模式（前端热更新）——双击 `start.bat`，或：
```bash
# 终端 A
cd backend && python run.py                       # http://127.0.0.1:8000
# 终端 B
cd frontend && npm run dev                        # http://127.0.0.1:5173（/api 自动代理）
```

> 端口被占用时，可设环境变量 `RR_PORT=8100` 换端口；开发模式下再设 `RR_BACKEND=http://127.0.0.1:8100` 让 Vite 代理指向它。

## 使用流程

1. 左侧拖拽/选择上传 PDF（支持多选），等待解析完成。
2. 顶部选一个技能（按分类分组），按需勾选「视觉校正图表」（需带视觉能力的模型）。
3. 点「▶ 开始分析」→ 切到 **AI 精读**：总览、指标卡、可交互图表、章节、数据表、风险、追问。
4. 图表点「定位第 N 页」跳到 **原 PDF** 对应页并高亮；「分析记录」里可查看/删除历史分析。
5. 需要干净的阅读体验时点 🧘 专注；阅读完成后可「📤 导出 HTML」离线分享。

## Skills（可插拔技能）

内置 **14 个技能，分 6 类**：

| 分类 | 技能 |
| --- | --- |
| 个股与公司 | `stock-deep`（个股深度）、`earnings-flash`（业绩快评）、`quant-fundamental`（基本面量化） |
| 行业与配置 | `industry-research`（行业全景）、`quant-portfolio`（组合优化与资产配置）、`industry-rotation`（行业景气度与轮动） |
| 金工与量化 | `quant-strategy-eval`（策略评审）、`quant-factor`（多因子）、`quant-ml`（机器学习量化）、`event-arbitrage`（事件驱动与套利） |
| 风险与固收 | `quant-risk`（风险管理与归因）、`bond-cb`（固收与可转债） |
| 加密资产 | `crypto-research`（加密货币研究） |
| 学术与论文 | `academic-paper`（论文精读） |

**新增技能**＝在 `backend/skills/` 下建一个文件夹（增删改即生效，无需重启；重新打开 Skills 面板刷新列表即可）：

```
skills/my-skill/
├── SKILL.md     # YAML frontmatter + 正文（正文作为分析补充说明 instructions）
└── prompt.md    # 提示词模板（含占位符）；缺失则回退用 SKILL.md 正文
```

`SKILL.md` frontmatter 字段：

| 字段 | 说明 |
| --- | --- |
| `name` | 界面显示名 |
| `category` | 技能分类（下拉/面板按它分组，缺省「其他」） |
| `description` | 简介 |
| `version` / `author` / `tags` | 元信息（`tags` 逗号分隔） |
| `report_types` | 适用研报类型（逗号分隔） |
| `needs_vision` | `true/false`，默认是否建议启用视觉校正 |
| `uses_text_model` | 默认 `true` |

`prompt.md` 可用占位符（后端自动填充）：`{{title}}`、`{{n_pages}}`、`{{text}}`（逐页正文，超长截断）、`{{tables}}`（抽取到的表格）、`{{pages_json}}`、`{{instructions}}`、`{{chart_hints}}`。

模型被要求严格输出统一 JSON（总览/指标/要点/章节/图表/表格/风险/问题）；后端 `_normalize_result` 做数值清洗与容错，前端据此渲染。**所有技能共用同一契约，新增技能无需改前端。** 也可在「🧩 Skills」里用 `.zip` 安装（zip 内含一个带 `SKILL.md` 的目录）。

## 导出独立 HTML

在「AI 精读」顶部点「📤 导出 HTML」，生成**单文件自包含** HTML（内联本地 `echarts.min.js`，离线可打开、可分享；缺库时回退 CDN）。正文/指标/表格由后端直接渲染（无 JS 也能阅读、可打印），图表可交互。

## 后端 API 一览（`/api`）

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/health`、`/ai/status` | 健康与当前生效的 AI 配置 |
| POST | `/documents` | 上传并解析 PDF（multipart `file`） |
| GET | `/documents`、`/documents/{id}` | 列表 / 详情（含逐页、表格） |
| GET | `/documents/{id}/pdf`、`/pages/{n}.png` | 原 PDF / 逐页图 |
| DELETE | `/documents/{id}` | 删除（文件移入 `data/.trash`，可恢复） |
| POST | `/analyze` | 运行分析（`{doc_id, skill_id, use_vision}`） |
| GET | `/analyses/{id}`、`/documents/{id}/analyses` | 取分析结果 / 列表 |
| GET | `/analyses/{id}/export` | 导出独立 HTML（`?inline=1` 浏览器内查看） |
| GET/POST | `/skills`、`/skills/{id}/toggle`、`/skills/install` | 技能列表 / 开关 / zip 安装 |
| GET/POST | `/settings/ai`、`/settings/ai/active`、`/settings/ai/test`、`/settings/ai/key` | AI 配置：读取 / 保存某厂商档位 / 启用 / 测试 / 清 Key |

## 数据与隐私

- 默认仅监听 `127.0.0.1`；上传的 PDF、逐页图、SQLite、AI 配置全部在 `backend/data/`（**已 gitignore，不会提交**）。
- API Key 只存本机（`data/ai_config.json` 的对应厂商档位，或 `.env`），界面读取时**一律打码**；仓库源码中**不含任何 Key**。
- 只有「分析」这一步会把研报文本/图表页发给你配置的 AI 接口；不做分析则完全本地。

## 常见问题

- **分析报 429 / 401**：Key 无效或额度不足；在「⚙️ 设置」里换厂商档位/Key，或设 `OPENAI_BASE_URL` 指向可用网关。
- **OpenCode Go 报 `MissingSessionID`**：该网关要求请求头，在设置里给该厂商加 `x-opencode-session: <固定串>`。
- **表格没识别到**：`find_tables` 依赖表格边框线；无框线排版会从正文识别数值，也可勾选「视觉校正」。
- **改了 `backend/skills/` 没生效**：重新打开一次「🧩 Skills」刷新列表（每次打开都重新扫描）。
- **前端改了没更新**：`Ctrl+F5` 硬刷新；生产模式需重新 `npm run build`。
- **静态资源 404**：重新 `npm run build` 后需**重启后端**（StaticFiles 缓存目录）。

## License

MIT，详见 [LICENSE](LICENSE)。
