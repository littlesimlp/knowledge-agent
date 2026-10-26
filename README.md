# Knowledge Agent

> 用 Agent 把「读过的技术资料」变成「记得住、找得到、可追溯」的知识。
>
> An AI-assisted personal knowledge base: an Agent-driven tool that turns scattered
> technical materials into searchable, traceable knowledge.

![CI](https://github.com/littlesimlp/knowledge-agent/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.146-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)

**当前状态：M0 / M1 已完成，M2 的文本导入链路（M2-1 ~ M2-4）已可实际使用——可以用一条命令把
`.md` / `.txt` 笔记存进知识库。下一步 M2-5：PDF 解析。**
进度、已知的坑与决策详见 [`docs/handoff/00-project-state.md`](docs/handoff/00-project-state.md)。

---

## 这是什么

学习 AI / Agent / 软件工程时，我们持续接触论文、文档、代码片段和个人笔记。
这些资料读过了、存下了，但几个月后既想不起内容，也搜不到位置，于是重复搜索、重复阅读。

本项目要解决的就是这个问题：一个可以长期积累、组织、检索和更新的个人技术百科。

**三条不可违背的业务规则：**

1. AI 是辅助，不是知识库运行的必要条件——模型不可用时，手动增删改查和关键词检索照常工作。
2. 原始输入与来源必须保留，可追溯。
3. 内容相关 ≠ 内容相同。**绝不自动合并**；AI 对已有内容的修改**必须经用户确认**。

## 技术栈

| 层 | 选型 | 状态 |
|---|---|---|
| 后端 | Python 3.12 + FastAPI + uvicorn | ✅ 已使用 |
| ORM | SQLAlchemy 2.x（async）+ asyncpg | ✅ 已使用 |
| 数据库迁移 | Alembic（async 模板） | ✅ 已使用 |
| 数据库 | PostgreSQL 16（Docker） | ✅ 已使用 |
| 容器编排 | Docker Compose | ✅ 已使用 |
| 依赖管理 | uv（`pyproject.toml` + `uv.lock`） | ✅ 已使用 |
| 测试 | pytest + pytest-asyncio + httpx | ✅ 已使用 |
| Lint | ruff（显式规则集） | ✅ 已使用 |
| CI | GitHub Actions（含真实 PostgreSQL） | ✅ 已使用 |
| 文件解析 | PyMuPDF、Markdown/TXT 解析 | ⬜ M2 引入 |
| 前端 | React + TypeScript + Vite | ⬜ M3 之后引入 |

架构为**模块化单体**，不采用微服务。所有数据库访问都是异步的。

## 快速开始

### 前置要求

| 工具 | 版本 | 说明 |
|---|---|---|
| git | 任意较新版本 | |
| Docker Desktop | 含 Docker Compose v2 | **必需**，数据库跑在容器里 |
| uv | 0.10+ | 本地开发（跑测试 / lint / 迁移）需要 |

> Python 不需要自己装——`uv` 会按 `.python-version` 自动准备 3.12。

### 五步启动

```bash
# 1. 克隆
git clone https://github.com/littlesimlp/knowledge-agent.git
cd knowledge-agent

# 2. 创建本地配置（.env 不进版本库）
cp .env.example .env
#    然后编辑 .env，把 POSTGRES_PASSWORD 改成你的密码

# 3. 构建并启动（首次会下载镜像，约 1–3 分钟）
docker compose up -d

# 4. 确认服务健康
docker compose ps
#    db   → Up (healthy)
#    api  → Up (healthy)

# 5. 验证接口
curl http://127.0.0.1:8000/health
#    {"status":"ok"}
```

交互式 API 文档：<http://127.0.0.1:8000/docs>

> **Windows PowerShell 用户注意**：`curl` 在 PowerShell 5.1 里是 `Invoke-WebRequest` 的别名，
> 输出不是原始 JSON。请改用 `curl.exe http://127.0.0.1:8000/health`。
> 写数据（POST / PATCH）建议直接用 `/docs` 页面，避免命令行引号转义问题。

### 本地开发模式（推荐日常使用）

容器里的 API 是构建那一刻的快照，改代码要重新 build。日常开发应让 **API 跑在宿主机、数据库仍在容器**：

```bash
docker compose stop api          # 释放 8000 端口，避免冲突
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

改完代码存盘即自动重载。容器里的 api 只在 CI 和部署验证时使用。

### 常用命令

```bash
# 数据库
docker compose up -d                                   # 启动 db（和 api）
docker compose ps                                      # 查看状态
docker compose logs -f db                              # 跟踪日志
docker compose exec -T db psql -U knowledge -d knowledge   # 进 psql
docker compose down                                    # 停止（数据保留在卷里）

# 后端
cd backend
uv run python -m pytest -q                             # 跑测试
uv run ruff check .                                    # 跑 lint
uv run alembic current                                 # 当前迁移版本
uv run alembic upgrade head                            # 应用未执行的迁移
```

> ⚠️ **永远不要执行 `docker compose down -v`** ——那个 `-v` 会连数据卷一起删除，本地数据不可恢复。
>
> ⚠️ **本地不要在开发库上执行 `alembic downgrade`** ——它会 DROP 表。需要验证迁移可逆性时切到测试库（见下）。

## 测试

测试使用**独立的数据库** `knowledge_test`，每个测试跑在一个事务里并回滚，不会污染开发数据。

首次运行前需要建一次测试库：

```bash
docker compose exec -T db psql -U knowledge -d knowledge -c "create database knowledge_test;"
```

然后：

```bash
cd backend
uv run python -m pytest -q
# 28 passed
```

测试用 `httpx.AsyncClient` + `ASGITransport` 在进程内直连 ASGI 应用，**不启动真实服务、不占端口**。

## API 接口

| 方法 | 路径 | 状态码 | 说明 |
|---|---|---|---|
| GET | `/health` | 200 | 存活探针，不查库、不调模型 |
| POST | `/api/entries` | 201 | 创建知识条目 |
| GET | `/api/entries` | 200 | 列出条目（按创建时间倒序） |
| GET | `/api/entries/{id}` | 200 / 404 | 获取单条 |
| PATCH | `/api/entries/{id}` | 200 / 404 | 部分更新（只改传入的字段） |
| DELETE | `/api/entries/{id}` | 204 / 404 | 删除 |
| POST | `/api/imports/text` | 201 / 422 | 导入粘贴文本（JSON） |
| POST | `/api/imports/file` | 201 / 413 / 415 / 422 | 导入文本文件（multipart） |

### 导入一篇笔记（推荐方式）

```bash
curl -X POST http://127.0.0.1:8000/api/imports/file \
  -F "file=@我的笔记.md" \
  -F "title=笔记标题" \
  -F "category=Docker"
```

一次导入会写入三条记录：

1. `knowledge_sources` —— **原文全文**（`extracted_text`）+ 文件路径 + 200 字展示片段
2. `knowledge_entries` —— 知识条目（`content` 缺省等于原文）
3. `knowledge_entry_sources` —— 两者的关联

上传的文件落在 `backend/data/uploads/<uuid>.<ext>`（已 gitignore，不会进库）。
**磁盘文件名是重新生成的 uuid**，原始文件名只保存在 `source_name` 字段里用于展示——
这是防止路径穿越的必要措施。

支持的类型：`.txt` / `.md` / `.markdown` / `.pdf`，单文件默认上限 5 MB。
PDF 若没有文字层（扫描件），会返回 422 并说明需要 OCR——当前版本不支持 OCR。

> 创建示例（不使用导入接口时）：

```bash
curl -X POST http://127.0.0.1:8000/api/entries \
  -H "Content-Type: application/json" \
  -d '{"title":"标题","content":"正文","category":"分类"}'
```

> 时间字段（`created_at` / `updated_at`）返回 **UTC**，由前端负责转换为本地时间。
> 更新接口是 `PATCH`（部分更新），不是 `PUT`（整体替换）。
>
> ⚠️ **多行文本不要走 JSON 接口**——JSON 字符串不允许裸换行，会报 `422 Invalid control character`。
> 真实笔记请用上面的 `multipart` 文件接口。

## 项目结构

```
knowledge-agent/
├── docker-compose.yml            # db + api 两个服务
├── .env.example                  # 环境变量模板（.env 不进库）
├── .github/
│   ├── workflows/ci.yml          # CI：lint + 迁移可逆性 + test + docker build
│   └── pull_request_template.md
├── docs/
│   ├── 01-srs.md                 # 需求规格说明书
│   ├── 02-design.md              # 技术设计与实施基线
│   ├── handoff/                  # 项目状态、决策记录（新人先读这个）
│   └── journal/                  # 作者学习心得（内容不进库）
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── uv.lock                   # 精确依赖锁定，必须提交
    ├── alembic/                  # 迁移脚本（versions/ 下为生成物）
    ├── app/
    │   ├── main.py               # 应用入口
    │   ├── core/config.py        # 配置（环境变量 / .env）
    │   ├── db/                   # 引擎、session、Base
    │   ├── models/               # ORM 模型
    │   ├── schemas/              # 请求/响应契约
    │   ├── parsers/              # 文件解析（按后缀分发，PDF 在 M2-5 加入）
    │   ├── services/             # 业务服务（导入编排、文件落盘）
    │   └── api/routes/           # 路由
    ├── data/                     # 上传文件落盘（已 gitignore）
    └── tests/                    # pytest（独立测试库 + 事务回滚）
```

## 环境变量

`.env` 由 `.env.example` 复制而来，**不进入版本库**。

| 变量 | 用途 |
|---|---|
| `POSTGRES_USER` | 数据库用户名 |
| `POSTGRES_PASSWORD` | 数据库密码（本地开发用，不要复用真实密码） |
| `POSTGRES_DB` | 数据库名 |

应用侧的连接参数（`DB_HOST` 等）默认值为本机 `127.0.0.1:5432`；在 Docker Compose 里会被覆盖成服务名 `db`。
所以同一份配置既能在容器里跑、也能在宿主机跑。

新增配置项时，**必须同步更新 `.env.example`**，否则其他人拉下来会启动失败。

## 协作流程

> `main` 是受保护分支：**任何人都不直接推送 `main`**，所有改动必须走 Pull Request 且 CI 通过。

### 一次完整的改动

```bash
# 1. 同步主干
git checkout main
git pull --rebase

# 2. 建分支（命名规范见下）
git checkout -b feat/knowledge-source-model

# 3. 开发并提交
git add -A
git commit -m "feat(db): add knowledge source model"

# 4. 推送
git push -u origin feat/knowledge-source-model

# 5. 在 GitHub 上点 "Compare & pull request"，按模板填写描述
# 6. 等 CI 变绿 → 至少 1 人 Approve → Squash and merge
# 7. 合并后删除分支
```

### 分支命名

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feat/` | 新功能 | `feat/knowledge-crud` |
| `fix/` | 缺陷修复 | `fix/db-timeout` |
| `docs/` | 仅文档 | `docs/api-contract` |
| `refactor/` | 重构（不改行为） | `refactor/split-routers` |
| `chore/` | 构建、依赖、配置 | `chore/bump-deps` |

多人并行时可加人名前缀：`wx/feat-knowledge-crud`。

### 提交信息规范（Conventional Commits）

```
<type>(<scope>): <description>

feat(api): add knowledge entry CRUD endpoints
fix(db): handle connection pool exhaustion
docs(readme): clarify quick start steps
chore(deps): bump fastapi to 0.147
```

| type | 含义 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 只改文档 |
| `refactor` | 重构，不改变外部行为 |
| `test` | 只改测试 |
| `chore` | 构建、依赖、工具配置 |
| `ci` | CI 配置 |

### PR 要求

- 描述必须回答三件事：**做了什么 / 为什么 / 怎么验证**
- CI 的 `Lint & Test` 和 `Docker build` 必须全绿
- 涉及数据库结构的改动，**必须同时提交 Alembic 迁移**，并在 PR 里说明迁移是否可逆
- 涉及 `.env` 新增变量，必须同步更新 `.env.example`
- 新增接口或修改接口语义，必须更新本文档的「API 接口」一节

### 不要做的事

| ❌ | 原因 |
|---|---|
| 直接 push `main` | 分支保护会拒绝；即使能推也不要 |
| 提交 `.env` 或任何密钥 | 仓库是 public |
| 提交 `uv.lock` 的冲突残留 | 会让所有人的依赖装不上 |
| 对 `main` 使用 `git push --force` | 会覆盖他人提交；需要时用 `--force-with-lease` |
| 在开发库上跑 `alembic downgrade` | 会 DROP 表，数据不保留 |
| 手工改数据库结构而不写迁移 | 别人拉代码后环境不一致 |
| 把真实知识数据提交进库 | 隐私；`data/` 已在 `.gitignore` |

## 文档索引

| 文档 | 内容 | 读者 |
|---|---|---|
| [`docs/01-srs.md`](docs/01-srs.md) | 需求规格说明书 V1.0 | 所有人 |
| [`docs/02-design.md`](docs/02-design.md) | 技术设计与实施基线 | 所有人 |
| [`docs/handoff/00-project-state.md`](docs/handoff/00-project-state.md) | **项目当前状态、进度、已知的坑** | **新人必读** |
| [`docs/handoff/01-decisions.md`](docs/handoff/01-decisions.md) | 技术决策记录（为什么这样选） | 所有人 |

## 路线图

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 工程骨架：仓库、FastAPI、PostgreSQL、Docker、CI | ✅ 完成 |
| M1 | 知识条目 CRUD：SQLAlchemy 模型、Alembic 迁移、REST 接口、独立测试库 | ✅ 完成 |
| M2 | 文件解析（PDF / Markdown / TXT）+ 来源记录 | 🔜 进行中 |
| M3 | AI 整理建议（标题/摘要/关键词/分类）+ 确认式写入 | ⬜ |
| M4 | 基础 RAG 问答（PostgreSQL 全文检索 + 来源引用） | ⬜ |
| M5 | 备份恢复演练 + 真实部署 | ⬜ |

## License

本项目采用 [AGPL-3.0](LICENSE)。

选择它的原因：PDF 解析依赖 PyMuPDF（AGPL-3.0 双许可），而 AGPL 要求衍生作品以同样许可发布。
详见 `docs/handoff/01-decisions.md` 的 D-017。