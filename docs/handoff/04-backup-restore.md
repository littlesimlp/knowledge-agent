# 备份与恢复演练（M5-1a）

> 状态：**M5-1a / M5-1b 已完成（2026-11-06 / 2026-11-10）**；下一步 M5-2 部署。
> 结论：本地一次完整备份 + 独立库/独立目录恢复通过，行数与文件哈希全部一致。

## 1. 备份范围

| 对象 | 位置 | 是否进备份 |
|---|---|---|
| PostgreSQL 数据库 `knowledge` | Docker 卷 `personal-agent_pgdata` | ✅ `pg_dump -Fc` |
| 上传文件 | `backend/data/uploads/`（bind mount） | ✅ `tar.gz` |
| 代码 | git 仓库 | ❌ 由 git 管理 |
| `.env` / 密钥 | 本机文件 | ❌ **不进备份包**，单独存密码管理器 |
| 前端保存的 LLM 配置 | `backend/data/llm.json` | ❌ 含 key，不进备份包；恢复后重新填 |
| 备份产物 | `backups/`（本机） | ❌ 已 gitignore |

## 2. 一次完整备份

```powershell
cd D:\personal-agent
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dir = "backups\$ts"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# 数据库：容器内落盘再复制，避免 PowerShell 弄坏二进制
docker compose exec -T db pg_dump -U knowledge -d knowledge -Fc -f /tmp/knowledge.dump
docker compose cp db:/tmp/knowledge.dump "$dir\knowledge.dump"
docker compose exec -T db rm -f /tmp/knowledge.dump

# 上传文件：保留 uploads/ 前缀
tar -czf "$dir\uploads.tar.gz" -C backend\data uploads

# 每个上传文件的 SHA256，恢复后逐个比对
Get-ChildItem backend\data\uploads -File |
  Get-FileHash -Algorithm SHA256 |
  Select-Object Hash, @{n='Name';e={ Split-Path $_.Path -Leaf }} |
  Export-Csv "$dir\uploads-sha256.csv" -NoTypeInformation -Encoding UTF8
```

## 3. 恢复到独立环境

```powershell
# 一次性恢复库，不碰 knowledge
docker compose exec -T db psql -U knowledge -d knowledge -c "drop database if exists knowledge_restore;"
docker compose exec -T db psql -U knowledge -d knowledge -c "create database knowledge_restore;"

docker compose cp "$dir\knowledge.dump" db:/tmp/knowledge.dump
docker compose exec -T db pg_restore -U knowledge -d knowledge_restore --no-owner /tmp/knowledge.dump
docker compose exec -T db rm -f /tmp/knowledge.dump

# 解包到独立目录
$restore = "$dir\restore-data"
New-Item -ItemType Directory -Force -Path $restore | Out-Null
tar -xzf "$dir\uploads.tar.gz" -C $restore
```

## 4. 校验

```powershell
# 行数：两个库各跑一次，逐项比较
$sql = "select (select count(*) from knowledge_entries) as entries, (select count(*) from knowledge_sources) as sources, (select count(*) from knowledge_entry_sources) as links;"
docker compose exec -T db psql -U knowledge -d knowledge -c $sql
docker compose exec -T db psql -U knowledge -d knowledge_restore -c $sql

# 文件：数量 + 全量 SHA256（无输出 = 完全一致）
$orig = Get-ChildItem backend\data\uploads -File |
  ForEach-Object { "$($_.Name) $((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" } |
  Sort-Object
$copy = Get-ChildItem "$restore\uploads" -File |
  ForEach-Object { "$($_.Name) $((Get-FileHash $_.FullName -Algorithm SHA256).Hash)" } |
  Sort-Object
Compare-Object $orig $copy
```

## 5. 用恢复数据启动应用

```powershell
cd D:\personal-agent\backend
$env:DB_NAME = "knowledge_restore"
$env:DATA_DIR = (Resolve-Path "..\backups\<时间戳>\restore-data").Path
uv run uvicorn app.main:app --port 8001
```

另一个终端：

```powershell
(Invoke-RestMethod http://127.0.0.1:8001/api/entries).Count
curl.exe -sS "http://127.0.0.1:8001/api/search?q=Docker"

$body = @{ question = "Docker"; limit = 5 } | ConvertTo-Json
$res = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/ask" -Method Post -ContentType "application/json" -Body $body
$res.grounded
$res.citations.Count
```

> `/api/ask` 不要用 `curl.exe -d '{"question":"Docker"}'`：PowerShell 会吞掉引号，后端收到 `{question:Docker}`，
> 返回 `422 json_invalid`。这是命令写法问题，不是接口问题。

## 6. 本次演练记录（2026-11-06）

| 项 | 值 |
|---|---|
| 环境 | Windows + Docker Desktop；PostgreSQL 16-alpine |
| 备份目录 | `backups/20261106-153526/` |
| `knowledge.dump` | 22.9 KB |
| `uploads.tar.gz` | 358.4 KB |
| 备份耗时 | 1.8 s |
| 恢复耗时 | 2.8 s |
| entries / sources / links | 6 / 6 / 6（开发库与恢复库一致） |
| 上传文件 | 4 / 4，SHA256 全部一致 |
| 恢复库接口 | `/api/entries` 200、`/api/search` 200、`/api/ask` 200（`grounded=true`，1 条引用） |
| 开发库 | 演练前后 6 / 6 / 6，未变 |

## 7. 判定标准

1. 三张表行数逐项相等；
2. 上传文件数量相等，且 SHA256 全等；
3. 应用连恢复库能启动，`entries` / `search` / `ask` 正常；
4. 原开发库在演练前后不变。

## 8. RPO / RTO

| 指标 | 含义 | 当前 |
|---|---|---|
| RPO | 最多能接受丢多少数据 | 手工阶段：重大变更前备份；目标每日一次（M5-1b 后） |
| RTO | 从备份到服务可用 | 本次恢复 2.8 s；含人工操作目标 < 10 分钟 |

> 2.8 s 只是 `pg_restore` + 解包的时间，不含找文件、改配置、启动应用的耗时。

## 9. 已知限制

- 备份和数据在同一台机器（`D:\personal-agent\backups`），**不能防磁盘损坏**；需要异地/云盘副本。
- 备份未加密；dump 包含全部知识正文，注意存放权限。
- `.env` 和 `backend/data/llm.json` 不在包内；恢复后需要单独还原配置、重新填 key。
- 脚本已覆盖本地演练，但依赖本机 Docker Compose；CI 里还没有自动跑恢复演练。
- `knowledge_restore` 是一次性库，演练后应删除，避免占用。

## 10. M5-1b 一键演练（2026-11-10）

脚本 `backend/scripts/drill.py`，在 `backend/` 下运行：

```powershell
uv run python scripts\drill.py
uv run python scripts\drill.py --keep-restore
```

流程：`pg_dump` → 打包 uploads → 恢复到 `knowledge_restore` → 比对行数与 SHA256。
全部一致 `exit 0`；不一致或命令失败 `exit 1`；成功默认删除恢复库，失败或 `--keep-restore` 时保留。

### 本次结果

| 运行 | 结果 | 备份 | 恢复 | 行数 | 文件 |
|---|---|---|---|---|---|
| 首次 | PASS | 11.1 s | 2.6 s | 6,6,6 vs 6,6,6 | 4 vs 4，SHA256 全等 |
| 二次（`--keep-restore`） | PASS | 1.4 s | 2.4 s | 6,6,6 vs 6,6,6 | 4 vs 4，SHA256 全等 |
| 停 db 后 | FAIL | — | — | — | 退出码 1，`result : FAIL` |

首次 11.1 s 是冷启动（容器/文件缓存未热），二次 1.4 s 更接近稳定值。

## 11. 之后

1. 备份进计划任务（每日）；
2. 增加一份异地副本；
3. 每季度完整演练一次并更新本文件；
4. M5-2：同源部署（nginx + compose）。
