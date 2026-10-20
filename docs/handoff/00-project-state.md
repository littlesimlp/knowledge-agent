# 项目状态与交接文档

> **用途**：当对话上下文超长、更换 LLM、换机器、或隔几周回来时，把本文件完整贴给助手，
> 即可无缝接续，不必重述背景。
>
> **维护规则**：每完成一个里程碑更新一次。只写结论和现状，不写过程流水账。

- 最后更新：2026-10-19
- 当前里程碑：**M0 已完成**，M1 待开始
- 维护人：项目作者本人

---

## 1. 项目是什么

**一句话定位**：Agent 驱动的个人知识库 —— 用 Agent 把「读过的技术资料」变成「记得住、找得到」的知识。

| 项 | 内容 |
|---|---|
| 目标用户 | 先自己真实使用，再给身边熟人小范围试用 |
| 双重目的 | ① 学会从零构建到维护的完整工程流程 ② 作为 GitHub 作品集 / 实习竞争力 |
| 仓库 | https://github.com/littlesimlp/knowledge-agent |
| 本地路径 | `D:\personal-agent` |
| 默认分支 | `main` |

核心业务规则（来自需求文档，不可违背）：

1. AI 是辅助，不是知识库运行的必要条件
2. 原始输入与来源必须保留，可追溯
3. 内容相关 ≠ 内容相同，**绝不自动合并**
4. AI 对已有内容的修改**必须经用户确认**
5. 检索回答不得伪造条目、来源或原文依据

---

## 2. 技术栈（已冻结，不要随意更换）

| 层 | 选型 | 说明 |
|---|---|---|
| 后端框架 | Python 3.12 + **FastAPI** | 选 Python 的唯一决定性理由：AI 生态（PyMuPDF / LLM SDK / embedding） |
| HTTP 服务器 | **uvicorn** | 内嵌进程，无需单独安装 |
| 依赖管理 | **uv**（`pyproject.toml` + `uv.lock`） | 项目里**禁止**用 pip / conda |
| 数据库 | **PostgreSQL 16-alpine**（Docker） | 不用本机安装 |
| ORM | SQLAlchemy 2.0 | M1 才引入 |
| 迁移 | Alembic | 相当于 Flyway |
| 前端 | React + TypeScript + Vite | M2 之后才做 |
| 容器 | Docker Compose | 前端+后端+数据库 |
| 测试 | pytest（后端）、Vitest（前端） | |
| Lint | ruff（line-length=100） | |
| CI | GitHub Actions | 两个 job：Lint & Test、Docker build |
| 架构 | **模块化单体**，不用微服务 | |

---

## 3. 目录结构（当前实际状态）

```
D:\personal-agent\
├── .github\workflows\ci.yml      # CI：lint + test + docker build
├── .gitignore                    # 已排除 .env / data/ / .venv / node_modules
├── .gitattributes                # 强制 LF，防 CRLF 进容器
├── .env                          # 本地配置，不进 git
├── .env.example                  # 进 git，给 clone 的人看需要哪些变量
├── docker-compose.yml            # db + api 两个服务
├── docs\
│   ├── 01-srs.md                 # 需求规格说明书 V1.0
│   ├── 02-design.md              # 技术设计评审与实施基线 V1.0
│   ├── handoff\                  # ← 本文件所在：给 AI / 未来的自己
│   └── journal\                   # ← 作者的学习心得
└── backend\
    ├── Dockerfile                # python:3.12-slim + uv，多层构建
    ├── .dockerignore
    ├── .python-version           # 3.12
    ├── pyproject.toml            # 依赖 + pytest/ruff 配置
    ├── uv.lock                   # 精确版本锁定，进 git
    ├── app\
    │   ├── __init__.py
    │   └── main.py               # FastAPI 实例 + /health
    └── tests\
        └── test_health.py
```

---

## 4. 已完成（M0：工程骨架）

| 项 | 状态 | 证据 |
|---|---|---|
| 仓库与提交历史 | ✅ | 4 条提交，Conventional Commits 规范 |
| 提交身份 | ✅ | `753914+juner@…` 已废弃，现用 `72534653+littlesimlp@users.noreply.github.com` |
| FastAPI 服务 | ✅ | `GET /health` → `{"status":"ok"}` |
| PostgreSQL 容器 | ✅ | 16.15，命名卷 `personal-agent_pgdata`，healthcheck 通过 |
| API 容器 | ✅ | 镜像 294 MB，`depends_on: service_healthy` |
| 数据持久化 | ✅ | `down` → `up` 后数据仍在，已实测两次 |
| Docker 磁盘迁移 | ✅ | 已从 C 盘迁至 `D:\docker_data\DockerDesktopWSL`（C 盘回收 2.6 GB） |
| Lint | ✅ | ruff 全绿 |
| 测试 | ✅ | `1 passed` |
| CI | ✅ | run `87c8b9e`，17 秒，两个 job 全绿 |

---

## 5. 未完成 / 下一步

### M1（当前目标）：知识条目 CRUD

| 步骤 | 内容 | 状态 |
|---|---|---|
| M1-1 | 数据库连接配置 + SQLAlchemy 引擎 + Alembic 初始化 | ⬜ |
| M1-2 | `KnowledgeEntry` 模型 + 第一个迁移 | ⬜ |
| M1-3 | CRUD 接口（POST / GET list / GET one / PUT / DELETE） | ⬜ |
| M1-4 | 带测试数据库的 pytest（事务回滚隔离） | ⬜ |

### 之后

- **M2**：文件解析（PyMuPDF / Markdown / TXT）+ 来源记录 + 上传文件用 bind mount 存 `./data/`
- **M3**：AI 整理建议（标题/摘要/关键词/分类）+ 确认式写入
- **M4**：基础 RAG（PG 全文检索 → 交给模型 → 展示真实条目与来源）
- **M5**：备份恢复演练 + 真实部署给自己用
- 前端的引入时机待定（建议至少 M3 之后，先把 API 打通）

---

## 6. 关键技术决策摘要

详见 `01-decisions.md`。当前最重要的三条：

1. **全异步**（SQLAlchemy async + asyncpg）——理由：项目核心是 AI，I/O 密集，同步会成为 M4 的返工点。
2. **数据库用命名卷而非 bind mount**——Windows 上 bind mount 数据库目录会慢十倍且可能损坏数据。
3. **端口一律绑 `127.0.0.1`**——数据库和 API 都不暴露到局域网。

---

## 7. 已知的坑与固定约定（踩过的别再踩）

| 坑 | 现象 | 约定 |
|---|---|---|
| Anaconda 3.9 污染 PATH | `pytest` 用了 Python 3.9，报 `No module named 'fastapi'` | **所有 Python 命令一律 `uv run python -m xxx`**，不要裸用 `pytest` |
| `uv run` 静默回落 PATH | 命令"成功"但用错解释器 | 用 `uv run python -m pytest`，缺依赖会直接报错 |
| 中文目录名 | Compose 报 `project name must not be empty` | 项目已搬到 `D:\personal-agent`，**不要再放回中文路径** |
| CRLF | 容器里 `exec format error` / 诡异路径错误 | 编辑器一律存 LF，`.gitattributes` 已强制 |
| PowerShell 5.1 写文件 | `>` 重定向产生 UTF-16；`Set-Content -Encoding UTF8` 带 BOM | 一律用 `[System.IO.File]::WriteAllText(path, text)` |
| 容器里的 localhost | 连不上数据库 | 容器间用**服务名** `db:5432` |
| uvicorn 绑定地址 | 容器外访问不到 | 容器内必须 `--host 0.0.0.0` |
| GitHub 访问 | winget / push 超时 | 需要开 Clash（`127.0.0.1:7890`，git 已配代理） |
| Docker 数据增长 | C 盘被吃满 | 数据盘已在 D 盘；定期 `docker builder prune -f` |
| 删数据 | `down -v` 会删卷 | **永远不要**手贱 `docker compose down -v` |

其他约定：

- 提交信息用 **Conventional Commits**：`feat:` `fix:` `chore:` `docs:` `ci:` `refactor:` `test:`
- 配置/注释/Dockerfile 一律用**英文**，避免 Windows GBK 编码问题
- `.env`、`data/`、真实知识数据**永不进库**（仓库是 public）
- 推送前先看 `git status --short` 和 `git diff`
- 需要覆盖远端历史时用 `--force-with-lease`，**禁用** `--force`

---

## 8. 本机环境（已验证）

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
| Anaconda | 3.9.7 | `E:\anaconda` ⚠️ **不要用于本项目** |

运行状态：

- 服务地址：API `http://127.0.0.1:8000`，数据库 `127.0.0.1:5432`
- 容器名：`personal-agent-api-1`、`personal-agent-db-1`
- 卷名：`personal-agent_pgdata`
- Docker 数据盘：`D:\docker_data\DockerDesktopWSL`

---

## 9. 如何快速验证项目还活着

```powershell
cd D:\personal-agent
git pull                                  # 拿最新代码
docker compose ps                         # 两个服务应都 healthy
curl.exe http://127.0.0.1:8000/health     # {"status":"ok"}
docker compose exec -T db psql -U knowledge -d knowledge -c "select 1;"
```

CI 状态：

```powershell
$runs = curl.exe -s 'https://api.github.com/repos/littlesimlp/knowledge-agent/actions/runs?per_page=1' | ConvertFrom-Json
$runs.workflow_runs[0] | Select-Object name, head_sha, status, conclusion
```

---

## 10. 给新助手的开场提示（可直接复制）

> 我正在从零构建一个「Agent 驱动的个人知识库」，用于学习完整工程流程并作为 GitHub 作品集。
> 仓库：https://github.com/littlesimlp/knowledge-agent 本地：`D:\personal-agent`
> 请先读 `docs/handoff/00-project-state.md` 和 `docs/handoff/01-decisions.md` 了解现状与决策。
> 我的角色要求：**你只做引导和评审，不要直接写文件或改文件，除非我明确说「你来写」。**
> 每一步给我：做什么 → 验收标准 → 你会 review 什么。一次只给一个小目标。
> 我熟悉 Java + Spring + MySQL + Vue，不熟悉 Python 和 Docker，遇到 Python 特有概念请解释。
