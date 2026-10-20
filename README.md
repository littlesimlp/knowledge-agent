# Knowledge Agent

> 用 Agent 把「读过的技术资料」变成「记得住、找得到、可追溯」的知识。
>
> An AI-assisted personal knowledge base: an Agent-driven tool that turns scattered
> technical materials into searchable, traceable knowledge.

![CI](https://github.com/littlesimlp/knowledge-agent/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.146-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)

**当前状态：M0 工程骨架已完成（可运行、可测试、可复现）。业务功能从 M1 开始。**
进度与决策详见 [`docs/handoff/00-project-state.md`](docs/handoff/00-project-state.md)。

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
| 数据库 | PostgreSQL 16（Docker） | ✅ 已使用 |
| 容器编排 | Docker Compose | ✅ 已使用 |
| 依赖管理 | uv（`pyproject.toml` + `uv.lock`） | ✅ 已使用 |
| 测试 / Lint | pytest / ruff | ✅ 已使用 |
| CI | GitHub Actions | ✅ 已使用 |
| ORM / 迁移 | SQLAlchemy 2.0 / Alembic | ⬜ M1 引入 |
| 文件解析 | PyMuPDF、Markdown/TXT 解析 | ⬜ M2 引入 |
| 前端 | React + TypeScript + Vite | ⬜ M2+ 引入 |

架构为**模块化单体**，不采用微服务。

## 快速开始

### 前置要求

| 工具 | 版本 | 说明 |
|---|---|---|
| git | 任意较新版本 | |
| Docker Desktop | 含 Docker Compose v2 | **必需**，数据库和 API 都在容器里 |
| uv | 0.10+ | 可选，仅本地开发（跑测试/lint）时需要 |

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

# 4. 确认两个服务都健康
docker compose ps
#    db   → Up (healthy)
#    api  → Up (healthy)

# 5. 验证接口
curl http://127.0.0.1:8000/health
#    {"status":"ok"}
```

交互式 API 文档：<http://127.0.0.1:8000/docs>

> **Windows PowerShell 用户注意**：`curl` 在 PowerShell 5.1 里是 `Invoke-WebRequest` 的别名，
> 输出不是原始 JSON。请改用 `curl.exe http://127.0.0.1:8000/health`，或用
> `Invoke-RestMethod http://127.0.0.1:8000/health`。

### 常用命令

```bash
docker compose logs -f api          # 跟踪 API 日志
docker compose restart api          # 重启 API
docker compose down                 # 停止（数据保留在卷里）

cd backend
uv run python -m pytest -q          # 跑测试
uv run ruff check .                 # 跑 lint
uv run uvicorn app.main:app --reload --port 8000   # 本地开发（不用容器跑 API）
```

> ⚠️ **永远不要执行 `docker compose down -v`** ——那个 `-v` 会连数据卷一起删除，本地数据不可恢复。

## 项目结构

```
knowledge-agent/
├── docker-compose.yml        # db + api 两个服务
├── .env.example              # 环境变量模板（.env 不进库）
├── .github/workflows/ci.yml  # CI：lint + test + docker build
├── docs/
│   ├── 01-srs.md             # 需求规格说明书
│   ├── 02-design.md          # 技术设计与实施基线
│   ├── handoff/              # 项目状态、决策记录（新人先读这个）
│   └── journal/              # 作者学习心得（不进库，仅 README 公开）
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── uv.lock               # 精确依赖锁定，必须提交
    ├── app/main.py           # FastAPI 应用入口
    └── tests/                # pytest 测试
```

## 环境变量

`.env` 由 `.env.example` 复制而来，**不进入版本库**。

| 变量 | 用途 |
|---|---|
| `POSTGRES_USER` | 数据库用户名 |
| `POSTGRES_PASSWORD` | 数据库密码（本地开发用，不要复用真实密码） |
| `POSTGRES_DB` | 数据库名 |

新增配置项时，**必须同步更新 `.env.example`**，否则其他人拉下来会启动失败。

## 协作流程

> `main` 是受保护分支：**任何人都不直接推送 `main`**，所有改动必须走 Pull Request 且 CI 通过。

### 一次完整的改动

```bash
# 1. 同步主干
git checkout main
git pull --rebase

# 2. 建分支（命名规范见下）
git checkout -b feat/knowledge-crud

# 3. 开发并提交
git add -A
git commit -m "feat(api): add knowledge entry CRUD endpoints"

# 4. 推送
git push -u origin feat/knowledge-crud

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
- 涉及数据库结构的改动，必须同时提交 Alembic 迁移
- 涉及 `.env` 新增变量，必须同步更新 `.env.example`

### 不要做的事

| ❌ | 原因 |
|---|---|
| 直接 push `main` | 分支保护会拒绝；即使能推也不要 |
| 提交 `.env` 或任何密钥 | 仓库是 public |
| 提交 `uv.lock` 的冲突残留 | 会让所有人的依赖装不上 |
| 对 `main` 使用 `git push --force` | 会覆盖他人提交；需要时用 `--force-with-lease` |
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
| M1 | 知识条目 CRUD：SQLAlchemy 模型、Alembic 迁移、REST 接口、测试 | 🔜 进行中 |
| M2 | 文件解析（PDF / Markdown / TXT）+ 来源记录 | ⬜ |
| M3 | AI 整理建议（标题/摘要/关键词/分类）+ 确认式写入 | ⬜ |
| M4 | 基础 RAG 问答（PostgreSQL 全文检索 + 来源引用） | ⬜ |
| M5 | 备份恢复演练 + 真实部署 | ⬜ |

## License

尚未选定。在选定之前，默认保留所有权利。
