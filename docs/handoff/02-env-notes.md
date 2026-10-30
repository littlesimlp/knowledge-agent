# 新人环境记录（wx）

> 记录本机开发环境与安装过程中遇到的问题，供后续新人参考。
> 采集时间：2026-10-21

## 1. 环境清单

| 项目 | 值 | 备注 |
|---|---|---|
| 操作系统 | Windows 10 家庭中文版 22H2 (19045.6466) | |
| 终端 | Windows PowerShell 5.1.19041.6456 | 非 PowerShell 7 |
| git | 2.51.0.windows.1 | 已配置 GitHub 代理 `127.0.0.1:7897` |
| uv | 0.13.4 | |
| Python（项目） | 3.12 | 由 uv 自动下载，位于 `%APPDATA%\uv\python` |
| Node | v24.22.0 | 安装在 `E:\NodeJS`（非默认路径） |
| npm | 11.19.1 | 需用 `npm.cmd`（见问题 5） |
| Docker | 29.9.1 | **用户级安装**：`%LOCALAPPDATA%\Programs\DockerDesktop` |
| Docker Compose | v5.6.0 | |
| WSL | 3.0.1.0 / 内核 6.18.40.1 | 通过 GitHub Releases 的 MSI 安装 |
| PostgreSQL | 16.15 | `postgres:16-alpine` 容器 |
| Docker 数据盘 | `F:\docker-data\DockerDesktopWSL` | 已从 C 盘迁出 |
| pnpm | 未安装 | M2 再决定用 npm 还是 pnpm |

## 2. 安装与启动过程中遇到的问题

### 问题 1：git push 报 `Connection was reset`

- 现象：`git push` 时连接被重置，clone 却成功过
- 报错原文：`fatal: unable to access 'https://github.com/...': Recv failure: Connection was reset`
- 原因：本机直连 GitHub 被重置，git 不读取系统代理
- 解决：`git config --global http.https://github.com.proxy http://127.0.0.1:7897`（只对 GitHub 生效）
- 状态：已解决

### 问题 2：设代理后仍报 `schannel: failed to receive handshake`

- 报错原文：`fatal: unable to access '...': schannel: failed to receive handshake, SSL/TLS connection failed`
- 原因：git 默认使用 Windows 原生 TLS 后端（schannel），与本地代理组合时握手失败
- 解决：更换代理节点/模式后成功；备选方案是 `git config --global http.sslBackend openssl`
- 状态：已解决，但该链路不稳定，遇到时先换节点

### 问题 3：Docker 提示 "WSL needs updating"

- 现象：Docker Desktop 装好后无法启动引擎
- 根因：Windows 功能（WSL / 虚拟机平台）已启用并重启，但 **WSL2 内核未安装**
- 关键：`aka.ms/wsl2kernel` 现已指向文档网页，无法再下载旧的内核 MSI
- 解决：从 `https://github.com/microsoft/WSL/releases/latest` 下载 `wsl.3.0.3.0.x64.msi` 安装
- 验证：`wsl --version` 能输出版本即成功（注意 `C:\Windows\System32\lxss\tools\kernel` 检查法对 WSL 3.x 已失效）
- 状态：已解决

### 问题 4：winget 显示 Node.js 已安装，但文件不存在

- 现象：`winget list --name Node` 显示 24.20.0 已安装，但 `Test-Path 'C:\Program Files\nodejs\node.exe'` 为 False
- 原因：此前安装中途失败，winget 却写入了"已安装"记录
- 解决：`winget install --id OpenJS.NodeJS.LTS -e --force`；最终手动安装到 `E:\NodeJS`
- 教训：**判断软件是否可用要看文件本身，不能只看包管理器记录**
- 状态：已解决

### 问题 5：PowerShell 里 `npm` 报错，但 `npm.cmd` 正常

- 原因：PowerShell 优先匹配 `npm.ps1`，而执行策略为默认的 Restricted，禁止运行脚本
- 解决：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`；临时可用 `npm.cmd`
- 状态：已解决

### 问题 6：`docker compose up --build` 报 BuildKit 无法获取 token

- 报错原文：`failed to fetch oauth token: Post "https://auth.docker.io/token": dial tcp [2a03:...]:443`
- 关键线索：`docker pull postgres:16-alpine` **成功**，只有 `build` 失败
  → 守护进程的 DNS 正常，BuildKit 走的是 WSL 内部另一套 DNS，被污染
- 解决：`setx DOCKER_BUILDKIT 0`，让 compose 回退到旧版构建器
- 状态：已绕过（如需恢复 BuildKit，可给 Docker Desktop 配 HTTP 代理或配置 registry mirror）

### 问题 7：`docker-credential-desktop: executable file not found`

- 原因：Docker 装在用户目录，其 `resources\bin` 未进入当前进程 PATH
- 解决：新开终端即可（它与 `docker.exe` 在同一目录）
- 状态：已解决

### 问题 8：`docker compose up --build` 时报 `%PATH%` 相关错误

- 说明：同类问题的另一表现，根因都是 PATH 未刷新
- 通用解法：`Stop-Process -Name explorer -Force` 后重新开终端，或注销重登

### 问题 9：跑测试报 `database "knowledge_test" does not exist`

- 现象：`pytest` 全部报 `InvalidCatalogNameError`
- 原因：测试使用独立库 `knowledge_test`，需本地手动创建一次
- 解决：`docker compose exec -T db psql -U knowledge -d postgres -c "CREATE DATABASE knowledge_test;"`
- 状态：已解决

### 问题 10：curl 传中文 JSON 失败 / 显示乱码

- 现象：`curl.exe -d '{...}'` 报 `JSON decode error`；`Invoke-RestMethod` 中文显示乱码
- 原因：PowerShell 5.1 的引号转义与编码问题（非接口问题）
- 解决：调用接口优先用 `http://127.0.0.1:8000/docs` 页面；命令行则把 JSON 存成 UTF-8 无 BOM 文件后 `--data-binary @file`
- 状态：已解决

## 3. 验证结果（2026-10-21 实测）

| # | 验证项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 容器状态 | `docker compose ps` | db healthy |
| 2 | 迁移 | `uv run alembic upgrade head` | `8f8fc906784b (head)` |
| 3 | 测试 | `uv run python -m pytest -q` | **7 passed** |
| 4 | 风格检查 | `uv run ruff check .` | All checks passed |
| 5 | 健康检查 | `GET /health` | `{"status":"ok"}` |
| 6 | 创建条目 | `POST /api/entries` | 201，`workspace_id` 由服务端注入 |
| 7 | 列表 / 单条 | `GET /api/entries`、`/{id}` | 200 |
| 8 | 局部更新 | `PATCH /api/entries/{id}` | 200，仅改动传入字段 |
| 9 | 参数校验 | 空标题 | 422 |
| 10 | 不存在 | `GET /api/entries/{不存在id}` | 404 `知识条目不存在` |
| 11 | 删除 | `DELETE` → 再 `GET` | 204 → 404 |
| 12 | 中文存取 | 写入并查询 | 数据库中正确保存中文 |

> 注：开发时 API 跑在宿主机（`uv run uvicorn app.main:app --reload`），
> 容器 `api` 仅在 CI / 部署验证时使用。

## 4. 给文档的建议

| # | 位置 | 建议 |
|---|---|---|
| 1 | `00-project-state.md` §11「如何快速验证」 | 补一句：**首次跑测试前需手动创建 `knowledge_test` 库**，否则新人会卡在这一步 |
| 2 | `README.md` 前置要求 | 注明 Windows 用户如遇 BuildKit 报 DNS/token 错误，设置 `DOCKER_BUILDKIT=0` 可绕过 |
| 3 | `README.md` 前置要求 | Windows + PowerShell 需 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，否则 `npm` 不可用 |