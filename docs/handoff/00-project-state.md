# 项目状态与交接文档

> **用途**：当对话上下文超长、更换 LLM、换机器、或隔几周回来时，把本文件完整贴给助手，
> 即可无缝接续，不必重述背景。
>
> **维护规则**：每完成一个里程碑更新一次。只写结论和现状，不写过程流水账。

- 最后更新：2026-11-02
- 当前里程碑：**M3 已完成并合并**（PR #21）；M3-6 收尾（来源原文、删除二次确认、前端 CI）已完成，下一步 **M4（基础 RAG）**
- 配套文档：`01-decisions.md`（24 条决策）、`02-env-notes.md`（环境差异）、**`03-issue-log.md`（问题全记录）**
- 维护人：项目作者本人

---

## 1. 项目是什么

**一句话定位**：Agent 驱动的个人知识库 —— 用 Agent 把「读过的技术资料」变成「记得住、找得到、可追溯」的知识。

| 项 | 内容 |
|---|---|
| 目标用户 | 先自己真实使用，再给身边熟人小范围试用 |
| 双重目的 | ① 学会从零构建到维护的完整工程流程 ② 作为 GitHub 作品集 / 实习竞争力 |
| 仓库 | https://github.com/littlesimlp/knowledge-agent （public） |
| 本地路径 | `D:\personal-agent` |
| 默认分支 | `main`（受保护：必须走 PR + CI 通过） |
| 协作成员 | 作者本人 + 1 位协作者（GitHub 上有 Write 权限） |

核心业务规则（来自需求文档，不可违背）：

1. AI 是辅助，不是知识库运行的必要条件
2. 原始输入与来源必须保留，可追溯
3. 内容相关 ≠ 内容相同，**绝不自动合并**
4. AI 对已有内容的修改**必须经用户确认**
5. 检索回答不得伪造条目、来源或原文依据

---

## 2. 技术栈（已冻结，不要随意更换）

| 层 | 选型 | 状态 |
|---|---|---|
| 后端框架 | Python 3.12 + **FastAPI** | ✅ 已使用 |
| HTTP 服务器 | **uvicorn**（内嵌进程） | ✅ |
| 依赖管理 | **uv**（`pyproject.toml` + `uv.lock`） | ✅ 项目内**禁止** pip / conda |
| 数据库 | **PostgreSQL 16-alpine**（Docker） | ✅ |
| ORM | **SQLAlchemy 2.1（async + asyncpg）** | ✅ |
| 迁移 | **Alembic**（`-t async` 模板） | ✅ |
| 测试 | **pytest + pytest-asyncio + httpx** | ✅ 76 个测试 |
| Lint | **ruff**（显式规则集，见 D-013） | ✅ |
| CI | **GitHub Actions**（Lint & Test + Docker build + 前端 lint/build） | ✅ |
| 容器 | Docker Compose | ✅ |
| 文件解析 | PyMuPDF / Markdown / TXT | ✅ M2 已引入 |
| 前端 | React 19 + TypeScript + Vite | ✅ M3 已引入 |
| 架构 | **模块化单体**，不用微服务 |  |

---

## 3. 目录结构（当前实际状态）

```
D:\personal-agent\
├── .github\
│   ├── workflows\ci.yml               # CI：lint + 迁移可逆性 + test + docker build
│   └── pull_request_template.md       # 顶部含"PR 标题必须符合 Conventional Commits"提醒
├── .gitignore                         # 排除 .env / data/ / .venv / __pycache__ / journal 内容
├── .gitattributes                     # 强制 LF
├── .env                               # 本地配置（含真实 LLM_API_KEY），不进 git
├── .env.example                       # 进 git，含 POSTGRES_* 与 LLM_* 模板
├── LICENSE                            # AGPL-3.0（因 PyMuPDF 而选定，D-017）
├── docker-compose.yml                 # db（命名卷）+ api（bind mount ./backend/data）
├── README.md                          # 仓库门面 + 协作规范 + API 表
├── docs\
│   ├── 01-srs.md                      # 需求规格说明书 V1.0
│   ├── 02-design.md                   # 技术设计评审与实施基线 V1.0
│   ├── handoff\                       # 本文件 + 01-decisions + 02-env-notes + 03-issue-log
│   └── journal\                       # 学习心得（内容不进 git，只提交 README.md）
├── frontend\                          # React 19 + TS + Vite 8（M3-4 起）
│   ├── vite.config.ts                 # host 127.0.0.1 + /api 代理到 8000
│   ├── .oxlintrc.json                 # Oxlint（Rust linter，与后端 ruff 同路线）
│   └── src\
│       ├── main.tsx                   # 入口
│       ├── App.tsx                    # 条目列表 + 详情 + 建议预览
│       ├── api.ts                     # 只写相对路径的 fetch 封装
│       └── types.ts                   # 与后端 schema 手工对齐的类型
└── backend\
    ├── Dockerfile / .dockerignore     # 已含 alembic 文件，可在容器内跑迁移
    ├── .python-version                # 3.12
    ├── pyproject.toml                 # 依赖 + pytest / ruff 配置
    ├── uv.lock                        # 精确版本锁定，必须提交
    ├── alembic.ini
    ├── alembic\
    │   ├── env.py                     # 已改造：注入 sys.path + 从应用配置读 URL
    │   └── versions\                  # 迁移脚本（生成物，已从 ruff 排除）
    ├── data\                          # 上传文件落盘（git 已忽略；容器内为 /app/data）
    │   └── uploads\<uuid>.<ext>
    ├── app\
    │   ├── main.py                    # 应用入口：挂 3 个 router + /（跳 /docs）+ /health
    │   ├── core\config.py             # pydantic-settings；DB_* 与 LLM_* 两组配置
    │   ├── db\
    │   │   ├── base.py                # DeclarativeBase
    │   │   └── session.py             # async engine + AsyncSessionLocal + get_session
    │   ├── models\
    │   │   ├── knowledge_entry.py     # KnowledgeEntry（含 keywords ARRAY）+ DEFAULT_WORKSPACE_ID
    │   │   ├── knowledge_source.py    # KnowledgeSource / KnowledgeEntrySource / SourceType
    │   │   └── __init__.py            # 必须在此导入，否则 autogenerate 看不到
    │   ├── schemas\                   # API 契约层（与 ORM 分离）
    │   │   ├── knowledge_entry.py     # Create / Read / Update（含 Keywords 规范化）
    │   │   ├── knowledge_source.py    # Read（不含 extracted_text）
    │   │   ├── imports.py             # TextImportRequest / Result
    │   │   └── suggestions.py         # SuggestionRequest / Response
    │   ├── parsers\                   # 可插拔解析器
    │   │   ├── base.py                # ParseResult（含 pages）+ ParseStatus
    │   │   ├── text.py                # .txt / .md（多编码回退 + 换行归一）
    │   │   ├── pdf.py                 # PyMuPDF + 扫描件检测（D-018）
    │   │   ├── cleanup.py             # 页眉/页码过滤（D-016 两条规则）
    │   │   └── __init__.py            # SUPPORTED_SUFFIXES + parse_file 分发
    │   ├── services\                  # 业务编排
    │   │   ├── entries.py             # 连带删除（D-020）
    │   │   ├── imports.py             # 来源+条目+关联 一次事务写入
    │   │   ├── storage.py             # 落盘（uuid 重命名，防路径穿越）
    │   │   └── llm\                   # 模型适配层（D-021）
    │   │       ├── base.py            # EntrySuggestion + LLMProvider 协议 + LLMError
    │   │       ├── openai_compat.py   # 一个实现支撑 DeepSeek / SiliconFlow
    │   │       ├── fake.py            # 不联网的假实现
    │   │       └── __init__.py        # get_llm_provider 工厂
    │   └── api\
    │       ├── deps.py                # LLMDep + suggest_with_error_mapping
    │       └── routes\                # entries(7) / imports(2) / suggestions(1) / sources(1)
    └── tests\                         # 76 个测试，9 个文件
        ├── conftest.py                # 测试库 + 事务回滚隔离 + dependency_overrides
        ├── test_health.py             # 2
        ├── test_entries.py            # 12
        ├── test_imports.py            # 12
        ├── test_parsers.py            # 9
        ├── test_cleanup.py            # 8
        ├── test_pdf_parser.py         # 5
        ├── test_llm.py                # 12
        ├── test_suggestions.py        # 10
        └── test_sources.py            # 6
```

---

## 4. 数据模型现状

| 表 | 说明 | 状态 |
|---|---|---|
| `knowledge_entries` | 知识条目：id(uuid) / workspace_id / title / content / summary / category / created_at / updated_at | ✅ 已建 |
| `alembic_version` | Alembic 自己维护的迁移版本 | ✅ |
| `knowledge_sources` | 来源：source_type / source_name / source_url / file_path / **extracted_text** / source_excerpt / created_at | ✅ 已建 |
| `knowledge_entry_sources` | 条目↔来源 关联表（联合主键 + 两个 CASCADE 外键） | ✅ 已建 |

`knowledge_entries` 的完整列：`id` / `workspace_id` / `title(200)` / `content` / `summary` /
`category(100)` / **`keywords ARRAY(VARCHAR(50))`** / `created_at` / `updated_at`

- `DEFAULT_WORKSPACE_ID = 00000000-0000-0000-0000-000000000001`，第一版所有数据都落在这个空间（决策 D-003）
- `source_type` 存 VARCHAR(20) 而非原生 enum（便于扩展取值）
- `keywords` 用 PostgreSQL 原生数组（D-022）：可 `WHERE 'docker' = ANY(keywords)` 精确查询
- 当前迁移 head：`8d1a0cbf84bd`（add keywords to knowledge entries）

**数据一致性**：删除条目时如何处理来源与磁盘文件，已由 **D-020** 拍板为"连带删除"，
实现见 `app/services/entries.py`（只删已无其它引用的来源；先提交事务再删文件）。

---

## 5. API 契约（当前）

| 方法 | 路径 | 状态码 | 说明 |
|---|---|---|---|
| GET | `/health` | 200 | 存活探针，不查库不调模型 |
| GET | `/` | 307 | 重定向到 `/docs`（不在 schema 中） |
| POST | `/api/entries` | 201 | 创建；body 见 `KnowledgeEntryCreate`（含 keywords） |
| GET | `/api/entries` | 200 | 列表，按 `created_at` 倒序，限定 workspace |
| GET | `/api/entries/{id}` | 200 / 404 | 单条 |
| PATCH | `/api/entries/{id}` | 200 / 404 | 部分更新（`exclude_unset=True`），确认式写入走它 |
| DELETE | `/api/entries/{id}` | 204 / 404 | 删除，连带清理孤儿来源与文件（D-020） |
| GET | `/api/entries/{id}/sources` | 200 / 404 | 关联来源列表，**不含全文** |
| GET | `/api/sources/{id}` | 200 / 404 | 来源详情，含 `extracted_text`；跨空间一律 404 |
| POST | `/api/imports/text` | 201 / 422 | 导入粘贴文本（JSON body） |
| POST | `/api/imports/file` | 201 / 413 / 415 / 422 | 导入文件（multipart），支持 txt/md/pdf |
| POST | `/api/suggestions` | 200 / 503 | 对**一段纯文本**求 AI 整理建议，**不落库** |
| POST | `/api/entries/{id}/suggestions` | 200 / 404 / 422 / 503 | 对**已有条目**求建议，**不落库** |

**导入接口的状态码含义**：

| 码 | 触发条件 | 用户该看到 |
|---|---|---|
| 201 | 解析成功并入库 | 正常 |
| 413 | 文件超过 `max_upload_bytes`（默认 5 MB） | 文件太大 |
| 415 | 后缀不在 `SUPPORTED_SUFFIXES` 白名单 | 类型不支持（当前支持 txt/md/markdown/pdf） |
| 422 | 解析结果为空（`EMPTY`）或失败（`FAILED`） | 具体原因取自 `ParseResult.message` |

**建议接口的状态码含义**：

| 码 | 触发条件 | 客户端该做什么 |
|---|---|---|
| 200 | 成功（字段可能全为空 = 模型给不出建议，属正常结果） | 展示建议，让用户确认/编辑 |
| 422 | 条目正文为空白（不浪费模型调用） | 提示用户先补正文 |
| 503 | `LLMError`（无 key、超时、模型返回不可解析） | **降级为手动填写**，不要阻塞用户 |

交互式文档：<http://127.0.0.1:8000/docs>

> 查"接口是否存在"要用 **`app.openapi()["paths"]`**，不要遍历 `app.routes`
> —— 新版 FastAPI 会把 `include_router` 的内容包成 `_IncludedRouter`（见 03-issue-log G-5）。

返回的 `created_at` / `updated_at` 是 **UTC（带 Z）**，前端负责转本地时间。

---

## 6. 已完成

### M0：工程骨架

| 项 | 证据 |
|---|---|
| 仓库、提交历史、Conventional Commits | 提交身份为 `72534653+littlesimlp@users.noreply.github.com` |
| Docker 化（多层构建） | api 镜像约 294 MB，`.dockerignore` 排除 `.venv` |
| PostgreSQL + 命名卷持久化 | `personal-agent_pgdata`，`down` → `up` 数据不丢，实测两次 |
| 容器网络 | 容器间用服务名 `db:5432`；容器内 `localhost:5432` 报连接被拒 |
| Docker 数据盘迁移 | 已从 C 盘迁至 `D:\docker_data\DockerDesktopWSL`（C 盘回收 2.6 GB） |
| CI 首次跑通 | 两个 job 全绿 |

### M1：知识条目 CRUD

| 项 | 证据 |
|---|---|
| 配置层 | `app/core/config.py`，`AliasChoices` 同时兼容容器内 `DB_*` 与本机 `POSTGRES_*` |
| 异步引擎与会话 | `create_async_engine` + `AsyncSessionLocal` + `get_session` 依赖 |
| 数据模型 + 迁移 | `knowledge_entries` 8 列，uuid 主键，`server_default now()`，`workspace_id` 索引 |
| 迁移可逆 | `upgrade head` / `downgrade base` 都验证过 |
| 5 个 CRUD 端点 | 见第 5 节 |
| API 契约层 | Pydantic `Create` / `Read` / `Update`，与 ORM 分离 |
| 依赖注入 | `Annotated[AsyncSession, Depends(get_session)]`，规避 B008 |
| 测试隔离 | 独立库 `knowledge_test` + 每测试一事务 + `create_savepoint` 回滚 |
| 测试覆盖 | 7 passed：health 1 + entries 6（含一个"隔离机制生效"的元测试） |
| CI 带真实 PG | `services: postgres:16-alpine`，含 `alembic upgrade/downgrade` 检查 |
| CI 结果 | run `9b94177` → success，33 秒 |
| Lint 全绿 | 显式规则集 `E,F,I,UP,B,RUF`，忽略 `RUF001-003` |

---

## 7. 里程碑进度与下一步

### M2（已完成）：文件解析与来源

**实施顺序在 M2-2 时调整过（D-019）：先文本、后 PDF**，理由是"最小可用优先"——
真实使用后发现 JSON 接口无法导入多行文本，进一步印证了这个顺序。

| 步骤 | 内容 | 状态 |
|---|---|---|
| M2-1 | `KnowledgeSource` + `KnowledgeEntrySource` + 迁移 | ✅ PR #2 |
| M2-2 | 解析器基础设施 + TXT/Markdown 解析 + 10 个测试 | ✅ PR #3 |
| M2-3 | `POST /api/imports/text`：文本 → 来源 + 条目 + 关联 | ✅ PR #4 |
| M2-4 | 文件上传（multipart）+ 落盘 + 复用解析器 + 抽 service 层 | ✅ PR #5 |
| M2-5 | PDF 解析（PyMuPDF AGPL）+ 扫描件检测（D-018） | ✅ PR #8 |
| M2-6 | 页眉/页脚/页码噪音过滤（D-016 两条规则） | ✅ PR #11 |
| M2-7 | 连带删除来源与文件（D-020） | ✅ PR #13 |

PDF 实测：4772 → 4635 字符，每页精确删 2 行（页眉 + 页码），正文零误删。

### M3（已完成）：AI 整理建议 + 前端

| 步骤 | 内容 | 状态 |
|---|---|---|
| M3-1 | LLM 适配层：协议 + OpenAI 兼容实现 + fake + 工厂（D-021） | ✅ PR #14 |
| M3-2 | `POST /api/suggestions`：纯文本 → 建议（不落库） | ✅ PR #15 |
| M3-3 | `POST /api/entries/{id}/suggestions` + 抽出共用错误映射 | ✅ PR #16 |
| M3-4 | 前端骨架：列表 + 详情 + 建议预览（Vite 代理，D-023） | ✅ PR #17 |
| M3-4b | `keywords` 列 + 迁移 + 校验 + 前端类型同步（D-022） | ✅ PR #18 |
| M3-5 | 前端上传 + 建议可编辑表单 + 确认写入（PATCH） | ✅ PR #20 |
| M3-6 | 来源原文查看 + 删除二次确认 + 前端纳入 CI | ✅ 已完成 |

**M3 交付的完整闭环（已端到端实测）**：

```
选择文件 → POST /api/imports/file → 列表刷新
   ↓
点条目 → [让 AI 整理] → POST /api/entries/{id}/suggestions（不落库）
   ↓
可编辑表单（标题 / 摘要 / 分类 / 关键词）——草稿状态
   ↓
[保存] → PATCH /api/entries/{id} → 数据库确认
```

**验收记录（2026-10-30）**：经 Vite 代理完成上传 → 建议 → PATCH → 查库 → DELETE，
数据库实测 `端到端验收-已确认 | 验收 | {e2e,确认写入,M3}`，
删除后条目数与来源数相等（**无孤儿**，证明 D-020 的连带删除生效）。

### 之后（下一步）

- **M4**：基础 RAG
  1. PG 全文检索（`to_tsvector('simple', ...)`，中文暂用 simple 配置 + `keywords` 精确过滤）
  2. `POST /api/ask`：问题 → 检索相关条目 → 交给模型 → 回答**必须带条目引用**
  3. 前端加一个"提问"界面
- **M5**：备份恢复演练 + 真实部署给自己用
- 待补：暂无。原三项（前端 CI、删除二次确认、来源全文入口）已在 M3-6 补齐。

**测试规模**：后端 76 passed（9 个文件）；前端 lint 0 warnings、build 通过

---

## 8. 关键技术决策摘要

完整记录见 `01-decisions.md`。当前最重要的七条：

1. **全异步**（SQLAlchemy async + asyncpg）——项目核心是 AI，一次模型调用就是数秒 I/O（D-011）
2. **数据库用命名卷，上传文件用 bind mount**——前者不需要人看，后者需要在资源管理器里看到（D-007）
3. **端口一律绑 `127.0.0.1`**——包括前端（Vite 显式 `host`），都不暴露到局域网（D-008）
4. **测试用真实 PostgreSQL，不用 SQLite**——`Uuid`、`timestamptz`、`ARRAY` 在 SQLite 上行为不同（D-014）
5. **AI 不是必需品**——默认 `LLM_PROVIDER=fake`，模型不可用时基础功能照常（D-021）
6. **服务层用协议隔离供应商格式**——业务层连 "DeepSeek" 这个词都看不到（D-021）
7. **前端只写相对路径**——Vite 代理转发，生产同源部署零改动（D-023）

---

## 9. 已知的坑与固定约定（踩过的别再踩）

> **完整的"病历"（现象 → 根因 → 修复）见 [`03-issue-log.md`](03-issue-log.md)**，
> 按环境 / 版本控制 / 数据库 / 测试 / 解析器 / LLM / 前端分类。
> 下面的表只是速查清单。

| 坑 | 现象 | 约定 |
|---|---|---|
| Anaconda 3.9 污染 PATH | `pytest` 用了 Python 3.9，报 `No module named 'fastapi'` | **所有 Python 命令一律 `uv run python -m xxx`** |
| `uv run` 静默回落 PATH | 命令"成功"但用错解释器 | 用 `uv run python -m pytest`，缺依赖会直接报错 |
| **venv 不可搬迁** | 移动项目目录后 `uvicorn.exe` 报 `uv trampoline failed to canonicalize script path` | **删掉 `.venv` 重新 `uv sync`**；venv 里到处是绝对路径 |
| 中文目录名 | Compose 报 `project name must not be empty` | 已在 `D:\personal-agent`，**不要再放回中文路径** |
| CRLF | 容器里 `exec format error` | `.gitattributes` 已强制 LF；本地 CRLF / 仓库 LF 是安全的组合，但 `.sh` 脚本必须 LF |
| PowerShell 5.1 写文件 | `>` 产生 UTF-16；`Set-Content -Encoding UTF8` 带 BOM | 用 `[System.IO.File]::WriteAllText(path, text)` |
| **PowerShell 5.1 读文件** | `Get-Content` 默认按 GBK 解码 UTF-8，**看起来像文件损坏** | 用 `Get-Content x -Encoding UTF8`，或用 VS Code / 读取工具复核。**报"文件异常"前必须用第二种工具验证** |
| PowerShell `curl.exe -d` | 转义引号被吞，服务端收到 `{category:Docker}` | 用 `/docs` 页面写数据，或把 JSON 存文件后 `--data-binary @file` |
| `Invoke-RestMethod` 中文响应 | 显示 `é¨å` 乱码（数据本身正确） | 读接口用 `curl.exe`；PS 5.1 按 ISO-8859-1 解码响应 |
| **JSON body 传多行文本** | `422 json_invalid: Invalid control character at` | JSON 字符串不允许裸换行。**真实笔记一律走 `/api/imports/file`（multipart）** |
| **`write_text` 转译换行** | 测试里造 CRLF 输入，实际写出 `\r\r\n`，断言失败 | 测试辅助函数用 `write_text(..., newline="")` |
| **"追加" vs "整份替换"** | 让追加测试结果整份覆盖，丢了原有的 6 个测试 | 改完立刻 `pytest --collect-only -q` 核对**测试数量** |
| **文件建错目录/拼错名字**（4 次） | `ModuleNotFoundError` / `cannot import name 'suggestions'` | 先用 `New-Item -Path 完整路径` 建空文件；**建完立刻 `Get-ChildItem <dir> -File` 列目录** |
| **`git checkout -b X` 分支已存在** | 报 `already exists` 但人仍停原分支，提交全进 main | 建分支后 `git branch --show-current` 确认；优先 `git switch -c X origin/main` |
| **squash 合并后 `branch -d` 失效** | 原始提交不是 main 祖先 | 确认 PR 已 merged 后用 `git branch -D` |
| **PR 标题就是提交信息** | main 出现 `Docs/m2 progress` 这类提交 | PR 标题必须符合 Conventional Commits（已写进模板） |
| **分支基点太旧 → PR 冲突** | 差异里混入上一轮的 PR 内容 | `git reset --soft origin/main` 换基点；`push --force-with-lease` |
| **生成了迁移但没应用** | 测试绿（测试库由 metadata 建表），开发库缺列 | `alembic upgrade head` + `alembic current` 确认**测试绿 ≠ 已迁移** |
| **容器镜像是代码的快照** | 新接口在本地有、容器里 404 | 开发用 `docker compose stop api` + 本地 uvicorn；交付验证才 rebuild |
| **新版 FastAPI 的 `app.routes` 不可靠** | 遍历只看到 `/` 和 `/health` | 用 `app.openapi()["paths"]` 判断路由是否存在 |
| **Vite 默认只监听 IPv6** | `curl 127.0.0.1:5173` 连不上 | `vite.config.ts` 里 `host: "127.0.0.1"` |
| **`curl: (7) Failed to connect`** | — | **永远是"服务没起"**；`HTTP 404` 才是"服务在跑但没这个路由" |
| **中文路径经管道传给 Python** | `FileNotFoundError: 'F:\??\...'` | 脚本体保持纯 ASCII，路径走环境变量 |
| **`curl.exe` TLS 握手失败** | `schannel: failed to receive handshake` | 换 Node / Python 或换源；**不是网络封锁，别调配置** |
| **陈旧缓存** | 代码已改但报旧错误/旧 warning | 删 `.pytest_cache` 和 `__pycache__` 后重跑 |
| **测试夹具不真实** | 15 字符/页被 25 阈值判成扫描件 | **修夹具，不要降阈值**——削弱生产逻辑换绿测试是错误方向 |
| **新增格式改变旧测试预期** | 支持 `.pdf` 后 `.pdf` 从 415 变 422 | 新增能力时主动排查所有"否定/边界"类测试 |
| **用户文件名不可信** | 可能含 `../../config.py` | 只取后缀并白名单校验，磁盘名用 `uuid4().hex`；删除前校验路径前缀 |
| **删除文件必须先提交事务** | 事务回滚会留下指向不存在文件的记录 | 事务提交后再 `unlink`；失败只记日志 |
| 测试用的真实数据放错位置 | 仓库根目录出现未跟踪的真实笔记 | **测试数据只放 `backend/data/`（已 gitignore）或仓库外** |
| 容器里的 localhost | 连不上数据库 | 容器间用**服务名** `db:5432` |
| uvicorn 绑定地址 | 容器外访问不到 | 容器内必须 `--host 0.0.0.0` |
| GitHub 访问 | winget / push 超时 | 需要代理（`127.0.0.1:7890`）；临时绕过：`git -c http.proxy= -c https.proxy= push` |
| GitHub API 403 | 匿名配额 60 次/小时 | **配额按出口 IP 计**：加 `-x http://127.0.0.1:7890` 等于换一个配额池 |
| git 凭据助手 | `git: 'credential-manager-core' is not a git command` | `git config --global credential.helper manager` |
| **忘记 `git add`** | `git commit` 报 `no changes added to commit` | commit 前看 `git status --short` **第一列**：` M` 未暂存，`M ` 已暂存，`??` 未跟踪 |
| GitHub Action 版本 | `Set up job` 秒失败 | `astral-sh/setup-uv` **没有 `v10` 滚动 tag**，要用 `@v10.3.0` |
| Docker 数据增长 | C 盘被吃满 | 数据盘已在 D 盘；定期 `docker builder prune -f` |
| 删数据 | `down -v` 会删卷 | **永远不要**手贱 `docker compose down -v` |
| Python 文本编码 | `print` 中文乱码；`open()` 默认 cp936 | 用户环境变量 `PYTHONUTF8=1` |
| Alembic 位置 | 非 `backend/` 目录下报 `No 'script_location' key found` | 用 `uv run --directory backend alembic ...` |
| Alembic 找不到 app 包 | `ModuleNotFoundError: No module named 'app'` | `env.py` 里把 `backend/` 注入 `sys.path` |
| Alembic 密码含 `%` | configparser 插值报错 | `set_main_option` 前 `.replace("%", "%%")` |
| **Alembic autogenerate 会删表** | 库里手工建的表被当成"已删除"，生成 `drop_table` | **迁移文件必须人工 review**；开发库临时表先清掉 |
| **`alembic downgrade` 很危险** | 会 DROP 表，结构回滚但数据不保留 | 本地只用 `upgrade head`；验证可逆性切到 `knowledge_test` 再跑 |
| VS Code 新建文件落错目录 | `ModuleNotFoundError`（文件在 `app/` 而非 `app/models/`） | **先用 `New-Item -Path 完整路径` 建空文件**；或新建前先选中目标文件夹 |
| **`git checkout -b X` 分支已存在时静默失败** | 报 `already exists` 但人仍停原分支，提交全落到 main | 建分支后**立刻** `git branch --show-current` 确认；或改用 `git switch -c` |
| **squash 合并后 `git branch -d` 失效** | 原始提交不是 main 的祖先，`-d` 拒绝删除 | 确认 PR 已 merged 后，用 `git branch -D` 强删 |
| **PR 标题就是最终提交信息** | squash 后用分支名当标题，main 上出现 `Docs/m2 progress` 这种不合格提交 | PR 标题必须写 Conventional Commits 格式 |
| **中文路径通过管道传给 Python 会丢** | `$code \| uv run python -` 里写中文路径 → `FileNotFoundError: 'F:\??\???...'` | 脚本体保持纯 ASCII，中文路径走环境变量（`os.environ["PDF_PATH"]`） |
| **测试夹具不真实导致误判** | 合成 PDF 每页只 15 字符，被 D-018 的 25 阈值判成扫描件 | **修夹具，不要降阈值**——为让测试通过而削弱生产逻辑是最坏方向 |
| `curl.exe` 对某些站点 TLS 失败 | `schannel: failed to receive handshake`（gnu.org 等） | 换 Node / Python 或用代理；**这不是网络封锁，别浪费时间调配置** |

其他约定：

- 提交信息用 **Conventional Commits**：`feat:` `fix:` `chore:` `docs:` `ci:` `refactor:` `test:`
- **配置文件**（`.ini` / `.yml` / `.toml` / Dockerfile）注释用**英文**；Python 代码里可以用**中文**（见 D-013）
- `.env`、`data/`、真实知识数据**永不进库**（仓库是 public）
- 推送前先看 `git status --short` 和 `git diff`
- 需要覆盖远端历史时用 `--force-with-lease`，**禁用** `--force`
- 协作者加入后：`main` 走 PR 流程，不直接 push

---

## 10. 本机环境（已验证）

| 工具 | 版本 | 位置 |
|---|---|---|
| git | 2.55.0.windows.5 | `E:\git\Git\cmd` |
| uv | 0.10.11 | `C:\Users\jun\.local\bin\uv.exe` |
| Python（项目） | 3.12.13 | `backend\.venv`（uv 管理） |
| Python（容器内） | 3.12.15 | `/app/.venv` |
| Node | 24.20.0 (LTS) | `C:\Program Files\nodejs` |
| pnpm | 10.30.3 | npm 全局 |
| Docker | 29.8.2 | Docker Desktop |
| Docker Compose | v5.6.0 | 插件 |
| PostgreSQL（容器） | 16.15 (alpine) | |
| 关键 Python 依赖 | fastapi 0.146 / sqlalchemy 2.1.5 / asyncpg 0.32 / alembic 1.20 / pydantic 2.14 / pytest 9.1 / ruff 0.17 | |
| Anaconda | 3.9.7 | `E:\anaconda` ⚠️ **不要用于本项目** |

运行状态：

- 服务地址：API `http://127.0.0.1:8000`，数据库 `127.0.0.1:5432`
- 数据库：`knowledge`（开发）、`knowledge_test`（测试，跑完自动回滚）
- 容器名：`personal-agent-api-1`、`personal-agent-db-1`
- 卷名：`personal-agent_pgdata`
- Docker 数据盘：`D:\docker_data\DockerDesktopWSL`
- **开发时 API 跑在宿主机**（`uv run uvicorn app.main:app --reload`），容器 api 只在 CI / 部署验证时用

---

## 11. 如何快速验证项目还活着

```powershell
cd D:\personal-agent
git pull                                   # 拿最新代码
docker compose ps                          # db 应 healthy（api 可停）
docker compose exec -T db psql -U knowledge -d knowledge -c "select 1;"

cd backend
uv run python -m pytest -q                 # 期望 76 passed
uv run ruff check .                        # 期望 All checks passed
uv run alembic current                     # 期望 8d1a0cbf84bd (head)
uv run python -c "from app.main import app; p=app.openapi()['paths']; print(len(p), '条路径 /', sum(len(v) for v in p.values()), '个操作')"   # 期望 9 条路径 / 12 个操作

# 起后端（宿主机）
uv run uvicorn app.main:app --reload --port 8000
```

前端（另开一个终端）：

```powershell
cd D:\personal-agent\frontend
pnpm install
pnpm lint && pnpm build                    # 期望 0 warnings、build 成功
pnpm dev                                   # http://127.0.0.1:5173
```

端到端（经 Vite 代理，即前端真实路径）：

```powershell
curl.exe -sS http://127.0.0.1:5173/api/entries
```

CI 状态：

```powershell
$runs = curl.exe -sS -x http://127.0.0.1:7890 'https://api.github.com/repos/littlesimlp/knowledge-agent/actions/runs?per_page=1' | ConvertFrom-Json
$runs.workflow_runs[0] | Select-Object name, head_sha, status, conclusion
```

---

## 12. 给新助手的开场提示（可直接复制）

> 我正在从零构建一个「Agent 驱动的个人知识库」，用于学习完整工程流程并作为 GitHub 作品集。
> 仓库：https://github.com/littlesimlp/knowledge-agent 本地：`D:\personal-agent`
>
> **请先按顺序读完这四份文档，再开始任何操作：**
> 1. `docs/handoff/00-project-state.md`（现状、目录、API、坑表速查）
> 2. `docs/handoff/01-decisions.md`（22 条已定决策 D-001 ~ D-022，改设计前必读）
> 3. `docs/handoff/03-issue-log.md`（所有踩过的坑：现象 → 根因 → 修复）
> 4. `docs/handoff/02-env-notes.md`（本机与协作者机器的环境差异）
>
> **我的角色要求：你只做引导和评审，不要直接写文件或改文件，除非我明确说「你来写」。**
> 每一步给我：做什么 → 验收标准 → 你会 review 什么。一次只给一个小目标。
> 我在 VS Code 里手工建文件，所以请给出**清晰的「哪个文件、完整内容、新建还是覆盖」**，
> 终端命令只保留必须执行的那几条。
>
> **我最容易犯的四类错误，请主动提醒：**
> - 把「追加到文件末尾」做成「整份覆盖」（丢过测试）
> - 文件建错目录或名字拼错（4 次，报错信息都不指向真因）
> - 多文件改动时漏改其中一处（如 `SUPPORTED_SUFFIXES` 和白名单校验）
> - 分支基点太旧（`git pull` 没成功就切分支，导致 PR 冲突）
>
> 背景：我熟悉 Java + Spring + MySQL + Vue；不熟悉 Python 和 Docker。
> 我使用 Windows + PowerShell 5.1，编码和引号问题较多，涉及中文时请提示规避方式。
> 网络需要代理（`127.0.0.1:7890`），`curl.exe` 对部分站点 TLS 会失败（换 Node/Python）。
>
> **当前进度**：M0 工程骨架 / M1 条目 CRUD / M2 文件解析（txt+md+pdf+噪音过滤+连带删除）/
> **M3 AI 建议 + 完整前端（上传、可编辑确认表单、保存）——全部完成并已合并**
> （PR #1 ~ #21，后端 76 个测试，CI 全绿）。
>
> **下一步是 M4（基础 RAG）**：PG 全文检索 + `keywords` 精确过滤 → 交给模型 →
> 回答必须带真实条目与来源引用。前端要加一个"提问"界面。
