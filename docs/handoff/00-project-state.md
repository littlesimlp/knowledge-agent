# 项目状态与交接文档

> **用途**：当对话上下文超长、更换 LLM、换机器、或隔几周回来时，把本文件完整贴给助手，
> 即可无缝接续，不必重述背景。
>
> **维护规则**：每完成一个里程碑更新一次。只写结论和现状，不写过程流水账。

- 最后更新：2026-10-28
- 当前里程碑：**M2 已完成**（文本/PDF 导入 + 噪音过滤），下一步 M3（AI 整理建议 + 前端）
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
| 测试 | **pytest + pytest-asyncio + httpx** | ✅ 7 个测试 |
| Lint | **ruff**（显式规则集，见 D-013） | ✅ |
| CI | **GitHub Actions**（Lint & Test + Docker build） | ✅ |
| 容器 | Docker Compose | ✅ |
| 文件解析 | PyMuPDF / Markdown / TXT | ⬜ M2 引入 |
| 前端 | React + TypeScript + Vite | ⬜ M3 之后 |
| 架构 | **模块化单体**，不用微服务 |  |

---

## 3. 目录结构（当前实际状态）

```
D:\personal-agent\
├── .github\
│   ├── workflows\ci.yml               # CI：lint + 迁移可逆性 + test + docker build
│   └── pull_request_template.md
├── .gitignore                         # 排除 .env / data/ / .venv / __pycache__ / journal 内容
├── .gitattributes                     # 强制 LF
├── .env                               # 本地配置，不进 git
├── .env.example                       # 进 git
├── docker-compose.yml                 # db + api 两个服务
├── README.md                          # 仓库门面 + 协作规范
├── docs\
│   ├── 01-srs.md                      # 需求规格说明书 V1.0
│   ├── 02-design.md                   # 技术设计评审与实施基线 V1.0
│   ├── handoff\                       # ← 本文件 + 01-decisions.md
│   └── journal\                       # 学习心得（内容不进 git，只提交 README.md）
└── backend\
    ├── Dockerfile / .dockerignore
    ├── .python-version                # 3.12
    ├── pyproject.toml                 # 依赖 + pytest / ruff 配置
    ├── uv.lock                        # 精确版本锁定，必须提交
    ├── alembic.ini
    ├── alembic\
    │   ├── env.py                     # 已改造：注入 sys.path + 从应用配置读 URL
    │   └── versions\                  # 迁移脚本（生成物，已从 ruff 排除）
    ├── app\
    │   ├── main.py                    # 应用入口：挂 router + /health
    │   ├── core\config.py             # pydantic-settings，AliasChoices 兼容容器/本机
    │   ├── db\
    │   │   ├── base.py                # DeclarativeBase
    │   │   └── session.py             # async engine + AsyncSessionLocal + get_session
    │   ├── models\
    │   │   ├── knowledge_entry.py     # KnowledgeEntry + DEFAULT_WORKSPACE_ID
    │   │   └── __init__.py            # 必须在此导入，否则 autogenerate 看不到
    │   ├── schemas\
    │   │   └── knowledge_entry.py     # Create / Read / Update（API 契约层）
    │   └── api\routes\entries.py      # 5 个 CRUD 端点
    └── tests\
        ├── conftest.py                # 测试库 + 事务回滚隔离 + dependency_overrides
        ├── test_health.py
        └── test_entries.py
```

---

## 4. 数据模型现状

| 表 | 说明 | 状态 |
|---|---|---|
| `knowledge_entries` | 知识条目：id(uuid) / workspace_id / title / content / summary / category / created_at / updated_at | ✅ 已建 |
| `alembic_version` | Alembic 自己维护的迁移版本 | ✅ |
| `knowledge_sources` | 来源：source_type / source_name / source_url / file_path / **extracted_text** / source_excerpt / created_at | ✅ 已建 |
| `knowledge_entry_sources` | 条目↔来源 关联表（联合主键 + 两个 CASCADE 外键） | ✅ 已建 |

- `DEFAULT_WORKSPACE_ID = 00000000-0000-0000-0000-000000000001`，第一版所有数据都落在这个空间（决策 D-003）
- `source_type` 存 VARCHAR(20) 而非原生 enum（D-017 相关：便于扩展取值）
- 当前迁移 head：`3d2cb6bc4b94`（add knowledge sources and entry-source link）

**已知的数据一致性缺口（待决策）**：删除知识条目时，`ON DELETE CASCADE` 只清理关联表行，
**来源记录和磁盘文件会残留为"孤儿"**。三种处理方式（连带删除 / 保留并定期清理 / 不处理）
尚未决定，见 `01-decisions.md` 的待定条目。

---

## 5. API 契约（当前）

| 方法 | 路径 | 状态码 | 说明 |
|---|---|---|---|
| GET | `/health` | 200 | 存活探针，不查库不调模型 |
| POST | `/api/entries` | 201 | 创建；body 见 `KnowledgeEntryCreate` |
| GET | `/api/entries` | 200 | 列表，按 `created_at` 倒序，限定 workspace |
| GET | `/api/entries/{id}` | 200 / 404 | 单条 |
| PATCH | `/api/entries/{id}` | 200 / 404 | 部分更新（`exclude_unset=True`） |
| DELETE | `/api/entries/{id}` | 204 / 404 | 删除 |
| POST | `/api/imports/text` | 201 / 422 | 导入粘贴文本（JSON body） |
| POST | `/api/imports/file` | 201 / 413 / 415 / 422 | 导入文本文件（multipart） |

**导入接口的状态码含义**：

| 码 | 触发条件 | 用户该看到 |
|---|---|---|
| 201 | 解析成功并入库 | 正常 |
| 413 | 文件超过 `max_upload_bytes`（默认 5 MB） | 文件太大 |
| 415 | 后缀不在 `.txt/.md/.markdown` 白名单 | 类型不支持（PDF 在 M2-5 支持） |
| 422 | 解析结果为空（`EMPTY`）或失败（`FAILED`） | 具体原因取自 `ParseResult.message` |

交互式文档：<http://127.0.0.1:8000/docs>

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

## 7. 未完成 / 下一步

### M2（已完成）：文件解析与来源

**实施顺序在 M2-2 时调整过（D-019）：先文本、后 PDF**，理由是"最小可用优先"——
真实使用后发现 JSON 接口无法导入多行文本，进一步印证了这个顺序。

| 步骤 | 内容 | 状态 |
|---|---|---|
| M2-1 | `KnowledgeSource` + `KnowledgeEntrySource` + 迁移 | ✅ PR #2 |
| M2-2 | 解析器基础设施 + TXT/Markdown 解析 + 10 个测试 | ✅ PR #3 |
| M2-3 | `POST /api/imports/text`：文本 → 来源 + 条目 + 关联 | ✅ PR #4 |
| M2-4 | 文件上传（multipart）+ 落盘 + 复用解析器 + 抽 service 层 | ✅ PR #5 |
| M2-5 | PDF 解析（PyMuPDF AGPL）+ 扫描件检测（D-018：平均每页 < 25 字符 → EMPTY） | ✅ PR #8 |
| M2-6 | 页眉/页脚/页码噪音过滤（D-016：跨页重复短行 + 纯数字短行） | ✅ PR #11 |

**当前能力**：一条命令把 `.md` / `.txt` / `.pdf` 存进知识库，原文完整保存进
`knowledge_sources.extracted_text`，文件落在 `backend/data/uploads/`（git 已忽略）。
PDF 会自动清掉每页重复的页眉和页码（真实样本实测：4772 → 4635 字符，每页精确删 2 行、零误删）。

**测试规模**：42 passed。

### 之后

- **M3**：AI 整理建议（标题/摘要/关键词/分类）+ 确认式写入；**前端的引入时点**
  （现在只有 API，没有界面；实际使用后已明确感受到"手工 curl 太别扭"）
- **M4**：基础 RAG（PG 全文检索 → 交给模型 → 回答带真实条目与来源引用）
- **M5**：备份恢复演练 + 真实部署给自己用

**进 M3 前必须先拍板的**：D-020（删除条目后来源与磁盘文件的处理方式）。

---

## 8. 关键技术决策摘要

完整记录见 `01-decisions.md`。当前最重要的五条：

1. **全异步**（SQLAlchemy async + asyncpg）——项目核心是 AI，一次模型调用就是数秒 I/O；同步会在 M4 返工（D-011）
2. **数据库用命名卷而非 bind mount**——Windows 上 bind mount 数据库目录慢十倍且有损坏风险（D-007）
3. **端口一律绑 `127.0.0.1`**——数据库和 API 都不暴露到局域网（D-008）
4. **测试用真实 PostgreSQL，不用 SQLite**——`Uuid`、`timestamptz`、`server_default` 在 SQLite 上行为不同（D-014）
5. **ruff 显式规则集，忽略中文标点类规则**——中文注释用全角标点是正确书写（D-013）

---

## 9. 已知的坑与固定约定（踩过的别再踩）

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
| **JSON body 传多行文本** | `422 json_invalid: Invalid control character at` | JSON 字符串不允许裸换行。**真实笔记一律走 `/api/imports/file`（multipart）**，或用 Python 脚本 `json.dumps` |
| **`write_text` 转译换行** | 测试里造 CRLF 输入，实际写出 `\r\r\n`，断言失败 | 测试辅助函数用 `write_text(..., newline="")`；跨平台差异必须显式指定 |
| **"追加" vs "整份替换"** | 让追加测试结果整份覆盖，丢了原有的 6 个测试 | 改完立刻 `pytest --collect-only -q` 核对**测试数量**，比等 lint 报错快 |
| **用户文件名不可信** | 可能含 `../../config.py` 或 Windows 保留名 | 只取后缀并白名单校验，磁盘名用 `uuid4().hex` 生成；原始名只存 `source_name` 用于展示 |
| 测试用的真实数据放错位置 | 仓库根目录出现未跟踪的真实笔记 | **测试数据只放 `backend/data/`（已 gitignore）或仓库外**，用完即删 |
| 容器里的 localhost | 连不上数据库 | 容器间用**服务名** `db:5432` |
| uvicorn 绑定地址 | 容器外访问不到 | 容器内必须 `--host 0.0.0.0` |
| GitHub 访问 | winget / push 超时 | 需要开 Clash（`127.0.0.1:7890`）；临时绕过：`git -c http.proxy= -c https.proxy= push` |
| git 凭据助手 | `git: 'credential-manager-core' is not a git command` | 新版 GCM 名字是 `manager`：`git config --global credential.helper manager` |
| **忘记 `git add`** | `git commit` 报 `no changes added to commit` | commit 前看 `git status --short` **第一列**：` M` 是未暂存，`M ` 是已暂存，`??` 是未跟踪 |
| GitHub Action 版本 | `Set up job` 秒失败 | `astral-sh/setup-uv` **没有 `v10` 滚动 tag**，要用 `@v10.3.0`；`actions/checkout@v7` 有滚动 tag |
| Docker 数据增长 | C 盘被吃满 | 数据盘已在 D 盘；定期 `docker builder prune -f` |
| 删数据 | `down -v` 会删卷 | **永远不要**手贱 `docker compose down -v` |
| Python 文本编码 | `print` 中文乱码；`open()` 默认 cp936 | 用户环境变量 `PYTHONUTF8=1` |
| Alembic 位置 | 非 `backend/` 目录下报 `No 'script_location' key found` | 用 `uv run --directory backend alembic ...` |
| Alembic 找不到 app 包 | `ModuleNotFoundError: No module named 'app'` | `env.py` 里把 `backend/` 注入 `sys.path`（ruff 对 `sys.path` 后的 import 有 E402 豁免） |
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
docker compose ps                          # db 应 healthy
docker compose exec -T db psql -U knowledge -d knowledge -c "select 1;"

cd backend
uv run python -m pytest -q                 # 期望 7 passed
uv run ruff check .                        # 期望 All checks passed
uv run alembic current                     # 期望 8f8fc906784b (head)

# 起服务（宿主机）
uv run uvicorn app.main:app --reload --port 8000
```

CI 状态：

```powershell
$runs = curl.exe -s 'https://api.github.com/repos/littlesimlp/knowledge-agent/actions/runs?per_page=1' | ConvertFrom-Json
$runs.workflow_runs[0] | Select-Object name, head_sha, status, conclusion
```

---

## 12. 给新助手的开场提示（可直接复制）

> 我正在从零构建一个「Agent 驱动的个人知识库」，用于学习完整工程流程并作为 GitHub 作品集。
> 仓库：https://github.com/littlesimlp/knowledge-agent 本地：`D:\personal-agent`
> 请先读 `docs/handoff/00-project-state.md` 和 `docs/handoff/01-decisions.md` 了解现状与决策。
>
> **我的角色要求：你只做引导和评审，不要直接写文件或改文件，除非我明确说「你来写」。**
> 每一步给我：做什么 → 验收标准 → 你会 review 什么。一次只给一个小目标。
> 我在 VS Code 里手工建文件，所以请给出**清晰的「哪个文件、完整内容、新建还是覆盖」**，
> 终端命令只保留必须执行的那几条。
>
> 背景：我熟悉 Java + Spring + MySQL + Vue；不熟悉 Python 和 Docker。
> 我使用 Windows + PowerShell 5.1，编码和引号问题较多，涉及中文时请提示规避方式。
>
> 当前进度：M0（工程骨架）和 M1（知识条目 CRUD）已完成，CI 全绿。
> 下一步是 M2-1：新增 `KnowledgeSource` 和 `KnowledgeEntrySource` 两张表 + 迁移。
