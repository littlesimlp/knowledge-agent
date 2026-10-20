# 新人环境记录（wx）

> 记录本机开发环境与安装过程中遇到的问题，供后续新人参考。
> 采集时间：<2026-10-20>

## 1. 环境清单

| 项目 | 值 | 采集命令 / 备注 |
|---|---|---|
| 操作系统 | <Windows 11 家庭中文版 23H2 (22631)> | `[System.Environment]::OSVersion.VersionString` |
| 终端 | <PowerShell 7 / Windows PowerShell 5.1> | `$PSVersionTable.PSVersion` |
| git | <2.xx.x.windows.1> | `git --version` |
| uv | <未安装> | `uv --version`|
| Python | <3.12> | `uv run python --version`，由 uv 自动准备 |
| 编辑器 | <VS Code + 扩展> | |

## 2. 安装与启动过程中遇到的问题
### 问题 1：git push 时报 `Recv failure: Connection was reset`

- 发现时机：执行 `git push -u origin docs/wx-env-notes` 时
- 报错原文：`fatal: unable to access 'https://github.com/...': Recv failure: Connection was reset`
- 原因：本机访问 GitHub 直连被重置，git 默认不读取系统代理
- 解决方式：为当前终端设置 HTTP_PROXY / HTTPS_PROXY 指向本地代理端口后重试
- 状态：已解决

## 3. 快速开始五步验证结果

| # | 步骤 | 结果 |
|---|---|---|
| 1 | `git clone` / `git pull` | ✅ |
| 2 | `cp .env.example .env` 并改密码 | ✅ |
| 3 | `docker compose up -d` | ✅ 首次下载镜像约 <X> 分钟 |
| 4 | `docker compose ps` | ✅ db、api 均 healthy |
| 5 | `curl.exe http://127.0.0.1:8000/health` | ✅ 返回 `{"status":"ok"}` |

其他验证：
- API 文档 <http://127.0.0.1:8000/docs>：<✅ >
- `uv run python -m pytest -q`：<✅ / 未执行>
- `uv run ruff check .`：<✅ / 未执行>

## 4. 发现的文档问题与建议
未发现文档问题
| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| 1 | | | |
| 2 | | | |