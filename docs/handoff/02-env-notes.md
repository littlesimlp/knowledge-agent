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
未发现问题
五步启动
BASH
复制
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