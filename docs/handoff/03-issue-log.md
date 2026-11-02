# 开发问题全记录

> **用途**：按类别收录本项目从零到 M3 期间遇到的**所有非预期问题**，记录
> 「现象 → 根因 → 修复」，供日后排查与面试叙述使用。
>
> **与 `00-project-state.md` 第 9 节（坑表）的分工**：
> 坑表是**速查清单**（一行一条，防踩）；本文件是**病历**（讲清为什么会这样）。
>
> 最后更新：2026-10-30　覆盖范围：M0 ~ M3

---

## 0. 一句话总结

截至 M3，**没有一次故障是业务逻辑写错**。全部问题集中在四类：

| 类别 | 占比感受 | 本质 |
|---|---|---|
| 环境与工具链（Windows / PowerShell / TLS / 代理） | 最多 | 工具给你的输出不等于事实 |
| 版本控制历史（分支基点、squash 语义） | 次多 | 代码对，但"历史的形状"错了 |
| 配置与部署（迁移未应用、镜像过期） | 少数 | 改的是代码，跑的是旧的 |
| 真正的代码缺陷 | 很少 | 基本都是我给的示例片段本身的问题 |

**这个分布本身就是一条经验**：真实开发的瓶颈往往不在"想不出逻辑"，而在
"你以为在跑的东西，其实不是你在改的东西"。

---

## A. 环境与工具链

### A-1 PowerShell 读文件显示乱码（看起来像文件损坏）

- **现象**：`Get-Content pyproject.toml` 显示成"多行被合并成一行"或 `鍛藉悕鍗?`
- **根因**：PowerShell 5.1 的 `Get-Content` **默认按 GBK 解码**，而文件是 UTF-8
- **修复**：`Get-Content x -Encoding UTF8`，或用 VS Code / 读取工具复核
- **教训**：**报"文件损坏"之前必须用第二种工具验证**。本项目里这个假警报出现过 3 次
  （`pyproject.toml`、真实笔记 `.md`、LICENSE 行数差异）

### A-2 PowerShell 写文件产生 UTF-16 或 BOM

- **现象**：`>` 重定向出来的文件被改坏；`Set-Content -Encoding UTF8` 在 PS 5.1 带 BOM
- **根因**：PS 5.1 的默认编码是 UTF-16LE；`-Encoding UTF8` 实际写 UTF-8 **with BOM**
- **修复**：`[System.IO.File]::WriteAllText(path, text)`（UTF-8 无 BOM）

### A-3 中文路径经管道传给 Python 会丢失

- **现象**：`$code | uv run python -`，脚本里写 `F:\文件\...\x.pdf`，
  报 `FileNotFoundError: 'F:\??\???-???\???.pdf'`
- **根因**：PowerShell 把脚本文本通过管道以控制台编码（GBK）传给子进程，
  中文在传输中变成 `?`
- **修复**：**脚本体保持纯 ASCII**，中文路径走环境变量（Windows 环境变量内部是 UTF-16）
  ```powershell
  $env:PDF_PATH = 'F:\文件\...\x.pdf'
  $code = 'import os; path = os.environ["PDF_PATH"]'   # 纯 ASCII
  ```
- **教训**：跨进程边界传非 ASCII 文本，永远优先用环境变量或文件，不要用管道

### A-4 curl.exe 对部分站点 TLS 握手失败

- **现象**：`curl: (35) schannel: failed to receive handshake`（gnu.org、git-scm.com）
- **根因**：`curl.exe` 走 Windows schannel，证书吊销检查/协议协商会失败；
  **不是网络封锁，也不是代理问题**（走代理仍然失败，因为 TLS 是端到端）
- **修复**：换 `Node` / `Python urllib`（各自 TLS 栈）或改用其他源
- **实例**：AGPL 全文最后从 **GitHub License API** 取得（`/licenses/agpl-3.0`）

### A-5 代理客户端与端口

- **现象**：`git push` / `winget` 随机超时；后来发现 7890 的占用者变了
- **根因**：先装的是 Clash，后换成 `iKuuuVPNCore`，都监听 7890；代理没启动时
  git（配置了 `http.proxy=127.0.0.1:7890`）会直接失败
- **修复**：确认代理进程；必要时 `git -c http.proxy= -c https.proxy= push` 绕过
- **附注**：GitHub 匿名 API 配额按**出口 IP** 计。直连剩余 11/60、走代理 21/60，
  所以查 PR/CI 时加 `-x http://127.0.0.1:7890` 等于换了一个配额池

### A-6 Anaconda 3.9 抢占 PATH

- **现象**：`pytest` 报 `No module named 'fastapi'`；`uv run pytest` 也一样
- **根因**：系统里 Anaconda 3.9 在 PATH 靠前，`uv run pytest` 会回落到 PATH 上的 `pytest.exe`
- **修复**：**所有命令一律 `uv run python -m pytest`**（`-m` 强制用当前环境解释器）
- **约定**：本项目永不使用 `E:\anaconda` 的 Python

### A-7 venv 不可搬迁

- **现象**：项目目录改名后，`uvicorn.exe` 报 `uv trampoline failed to canonicalize script path`
- **根因**：`uv` 生成的入口脚本里写死了绝对路径
- **修复**：删掉 `.venv` 重新 `uv sync`
- **相关**：项目目录最初叫 `D:\个人知识库开发项目`，中文路径让 Compose 报
  `project name must not be empty`，因此迁移到 `D:\personal-agent`（英文）

### A-8 后台进程启动器失败

- **现象**：`spawn C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe ENOENT`
- **根因**：与项目无关的工具链瞬时故障
- **修复**：改用 `Start-Process` 直接起 `node`，或在前台终端手动运行

---

## B. Git / GitHub

### B-1 `git checkout -b X` 在 X 已存在时静默失败（后果最严重的一次）

- **现象**：无法创建 PR，提示"There isn't anything to compare"；
  `git log` 显示提交落在了**本地 main** 上
- **根因**：`git checkout -b` 遇到同名分支会**报错并停在原分支**，
  而人容易忽略那行 `fatal:`，后续所有提交都进了 main
- **修复**：
  ```bash
  git switch feat/pdf-parser
  git merge --ff-only main      # 把 main 的那个提交快进到分支
  git push -u origin feat/pdf-parser
  git switch main && git reset --hard origin/main
  ```
- **防御**：建分支后立刻 `git branch --show-current` 确认；优先用
  `git switch -c feat/xxx origin/main`（显式指定起点）

### B-2 squash 合并后 `git branch -d` 失效

- **现象**：`error: the branch 'feat/xxx' is not fully merged`，但它的 PR 明明已合并
- **根因**：`-d` 判断的是"提交是否为上游祖先"。squash 会生成**新哈希**，
  原始提交永远不是 main 的祖先
- **修复**：确认 PR 已 merged 后 `git branch -D`
- **教训**：删分支前该问的不是"git 说合并了吗"，而是**"它的 PR 合并了吗"**

### B-3 PR 标题会成为最终提交信息

- **现象**：main 上出现 `Docs/m2 progress`、`Merge pull request #10 from ...` 这类不合格提交
- **根因**：squash 合并用 **PR 标题**（或合并时编辑框的内容）作提交信息；
  GitHub 会用**分支名**自动填标题
- **修复/约定**：
  1. PR 标题必须写 Conventional Commits 格式（已写进 `pull_request_template.md`）
  2. 仓库设置里 `allowed_merge_methods` 只留 `squash`、squash 默认标题用 PR 标题

### B-4 分支基点太旧导致 PR 冲突

- **现象**：PR 提示 3 个文件冲突，而那一轮的改动实际只有 4 个文件的部分内容
- **根因**：新分支从**落后的本地 main** 切出（`git pull` 没成功），
  于是这一分支把上一个 PR 的内容又"新增"了一遍 → 两边同时新增同名文件
- **修复**（不重写代码，只换基点）：
  ```bash
  git reset --soft origin/main      # 只移动指针，不动工作区
  git commit -m "..."
  git push --force-with-lease origin feat/xxx
  ```
- **验证**：`git diff --stat origin/main..HEAD` 必须只包含本轮真正改的文件
- **教训**：`--soft` 是最安全的历史改写方式（内容零丢失）

### B-5 分支保护曾被绕过

- **现象**：规则生效后仍能直接 push main，日志出现 `Bypassed rule violations`
- **根因**：规则集的 `bypass_actors` 里含 RepositoryRole（含 write 角色）
- **修复**：清空 bypass 列表，之后得到预期的 `GH013: Repository rule violations found`

### B-6 CI 的两处配置坑

- `astral-sh/setup-uv@v10` → 404；必须用 `@v10.3.0`
- 首次 lint 56 个错误 → 显式 `select = ["E","F","I","UP","B","RUF"]` +
  `ignore = ["RUF001","RUF002","RUF003"]`（中文全角标点是正确书写）+
  `extend-exclude = ["alembic/versions"]`

---

## C. 数据库 / 迁移

### C-1 Alembic 必须在 backend/ 下运行

- **现象**：仓库根目录执行报 `No 'script_location' key found in configuration`
- **修复**：`cd backend` 或 `uv run --directory backend alembic ...`

### C-2 autogenerate 会把手工遗留表当成"应该删除"

- **现象**：生成的迁移里出现 `op.drop_table('pers_test')`
- **根因**：库里有手工建的表，模型里没有 → autogenerate 认为是"已删除"
- **修复**：删掉遗留表、删除迁移、重新生成
- **约定**：**迁移文件必须人工 review**，`upgrade()` 里出现 `drop_` 一律质疑

### C-3 `alembic downgrade` 很危险

- 结构会回滚，**数据不保留**。本地只用 `upgrade head`；
  验证可逆性交给 CI（`upgrade head` → `downgrade base`）和 `knowledge_test` 库

### C-4 生成迁移 ≠ 应用迁移

- **现象**：加了 `keywords` 字段、写了迁移文件、测试也过了，但**开发库里没有这一列**
- **根因**：测试库由 `Base.metadata.create_all` 直接建（**不读迁移**），
  所以测试能过；而开发库需要显式 `alembic upgrade head`
- **修复**：`uv run alembic upgrade head` + `alembic current` 确认到 head
- **教训**：**测试绿 ≠ 数据库已迁移**。这两条路径是独立的，必须分别验证

### C-5 容器镜像是"代码的快照"

- **现象**：前端请求 `/api/entries/{id}/suggestions` 返回 `{"detail":"Not Found"}`，
  但本地代码明明有这条路由
- **根因**：容器里的 api 是 3 天前构建的镜像，只有 5 条路由；本地代码有 7 条
- **修复**：交付形态验证用 `docker compose build api && docker compose up -d`；
  日常开发用 `docker compose stop api` + 本地 `uvicorn --reload`
- **做法**：**"改代码即生效"和"容器验证"要分成两个明确的动作，不要混用**

### C-6 新建文件落错目录（出现 4 次）

| 次数 | 报错 | 实际原因 |
|---|---|---|
| 1 | `No module named 'app.db.base'` | 建在 `alembic/` 而非 `app/db/` |
| 2 | `No module named 'app.knowledge_entry'` | 建在 `app/` 而非 `app/models/` |
| 3 | `No module named 'app.parsers.test_parsers'` | 建在 `app/parsers/` 而非 `tests/` |
| 4 | `cannot import name 'suggestions'` | 文件名拼成 `suggestiuons.py` |

- **修复**：先用 `New-Item -Path <完整路径>` 建空文件，再编辑
- **防御**：**建完立刻列目录**（`Get-ChildItem <dir> -File`）。
  第 4 次最难查——报错只说"找不到 suggestions"，完全没提拼错的文件名

---

## D. Python / 异步 / 测试

### D-1 测试夹具的换行被转译

- **现象**：`test_crlf_normalized` 期望 `行一\n行二`，实际得到多一个空行
- **根因**：`Path.write_text` 默认 `newline=None`，会把 `\n` 转成 `\r\n`，
  于是 `\r\n` 输入变成 `0D 0D 0A`
- **修复**：`write_text(..., newline="")`

### D-2 陈旧缓存让"已修复的问题"继续出现

- **现象**：代码已删掉 `TestClient`，pytest 仍报 `1 warning`
- **根因**：`.pytest_cache` / `__pycache__` 里是旧编译产物
- **修复**：删缓存后重跑 → `29 passed`（无 warning）
- **性质**：与 A-1 同一族——**工具给你的不是当前真相**

### D-3 测试夹具不真实，导致"看起来是阈值有问题"

- **现象**：合成的 PDF 每页只有 15 字符，被判成扫描件（EMPTY）
- **诱惑**：把 D-018 的阈值从 25 降到 10，"测试就绿了"
- **正确做法**：**修夹具**（每页写 8 行 ≈ 230 字符）
- **教训**：测试失败时先判断**谁错了**。为了让测试通过而削弱生产逻辑是错误方向——
  绿测试不等于对

### D-4 新增一种格式会改变"不支持"类测试的预期

- **现象**：支持 `.pdf` 之后，`test_import_unsupported_file_type` 从 415 变 422
- **根因**：`.pdf` 已在白名单内，请求进入解析器后失败 → 422 而非 415
- **修复**：该测试改用 `.docx`；新增 `test_import_broken_pdf_returns_422` 固定新行为
- **教训**：**新增能力时，主动排查所有"边界/否定"类测试**

### D-5 `__all__` 未排序（RUF022）

- ruff 的 isort 风格是"常量 → 类 → 函数"，与直觉的字母序不同
- **做法**：`ruff check . --fix`，不要手推规则

---

## E. 解析器 / PDF

### E-1 依赖体积

- PyMuPDF 连带 `numpy` / `onnxruntime`，镜像从 **294 MB 涨到 709 MB**
- 这是 PDF 提取质量的代价（D-017 已记录），构建时间也相应变长

### E-2 字符数差 1 个（4772 vs 4771）

- **现象**：独立分析算出 4772，入库后是 4771
- **根因**（精确可复现）：
  ```
  4772 −  4（4 页各丢一个页尾 \n）
       +  3（4 页之间 join 时加回 3 个 \n）
       = 4771
  ```
- **做法**：**把差异解释到字符级别**，而不是"差不多就行"。这类记录是评审最信服的东西

### E-3 页眉重复、页码每页不同 → 需要两条规则

- **现象**：真实 PDF 每页开头都有同一个页眉 + 各不相同的页码
- **发现**：D-016 原定"跨页重复的短行"**抓不到页码**（1、2、3 各不相同）
- **结论**：过滤器需要**两条**规则（跨页重复短行 + 极短纯数字行），已实现于
  `app/parsers/cleanup.py`（PR #11）
- **效果**：4772 → 4635 字符，每页精确删 2 行、零误删

### E-4 PDF 基础字体不含中文

- 测试里用 `page.insert_text` 只能写 ASCII（base14 字体限制）
- 真实中文 PDF 嵌入字体，提取正常——所以夹具用 `Page 1 line 1 ...` 这种英文标记

### E-5 AGPL 全文获取

- gnu.org 不可达（见 A-4），最终从 `https://api.github.com/licenses/agpl-3.0` 取得
- 校验方式：**字节数与 API 返回精确一致**（34,524 = 34,523 + 1 换行）
- 注意：`Measure-Object -Line` **忽略空行**（544），与按 `\n` 切分（662）不同口径

---

## F. LLM 适配层

### F-1 默认 provider 必须是 `fake`

- 没有 API key 时应用仍要能启动和运行 → `LLM_PROVIDER` 默认 `fake`
- 这也是业务规则 1（"AI 不是知识库运行的必要条件"）的落地方式

### F-2 解析模型输出必须做成纯函数

- 模型返回常被 ```json 包裹、前后带解释文字、字段类型错误
- 把 `parse_suggestion()` 做成**纯函数**后，不用真实 key、不联网就能完整覆盖这些风险
- **这是本轮最重要的可测试性决策**

### F-3 两个接口重复了错误映射

- 两处都要"调模型 + 把 `LLMError` 映射成 503 + 构造响应"
- **修复**：抽 `suggest_with_error_mapping()` 到 `app/api/deps.py`，一份语义

### F-4 配置通过构造注入，不读全局 settings

- `OpenAICompatProvider` 不 import `settings`（ruff F401 曾报"未使用"，
  其实是**有意的依赖注入**）：测试可直接构造指向假地址的实例，无需 monkeypatch 全局配置

---

## G. 前端

### G-1 Vite 默认只监听 IPv6

- **现象**：`curl 127.0.0.1:5173` 连不上，`localhost` 能通
- **根因**：`netstat` 显示只监听 `[::1]:5173`
- **修复**：`vite.config.ts` 里 `host: "127.0.0.1"`（也与 D-008 一致）

### G-2 Vite 代理是更好的跨域方案

- 前端只写相对路径 `/api/entries`；开发时 Vite 转发到 `127.0.0.1:8000`，
  生产同源部署时**代码零改动**
- 对比 CORS 中间件方案：后者要求前端硬编码后端地址

### G-3 长驻进程各占一个终端

- `uvicorn` 与 `pnpm dev` 都是前台进程，会占住终端
- **三个终端**：后端 / 前端 / 执行命令

### G-4 `curl: (7) Failed to connect` 的含义

- **永远是"服务没起或起在别的地址"**，不用怀疑业务代码
- 三层排查：① `netstat` 看端口 → ② `openapi.json` 看路由 → ③ 再发请求
- 对比：`HTTP 404` 才是"服务在跑但没有这个路由"（如 C-5 的旧镜像）

### G-5 新版 FastAPI 的 `app.routes` 不可靠

- **现象**：遍历 `app.routes` 只看得到 `/` 和 `/health`，看起来路由没注册
- **根因**：这个版本把 `include_router` 的内容包成 `_IncludedRouter` 对象，
  不再平铺到 `app.routes`
- **修复**：用 **`app.openapi()["paths"]`** —— 那是 `/docs` 的数据源，能看到的路径一定可访问

### G-6 前端类型必须与后端响应同步

- 后端加了 `keywords`，前端 `types.ts` 不同步 → TypeScript **不会报错**（多余字段被忽略），
  但下次用 `entry.keywords` 时编辑器说"不存在"
- **这是"隐性契约漂移"**，属于最难查的一类前端 bug

### G-7 脚手架会选择 linter

- `pnpm create vite` 新版会问 Oxlint / ESLint → 选 **Oxlint**（Rust 实现，与后端 ruff 同路线）

---

## H. 流程性教训（不是技术问题）

| 现象 | 教训 |
|---|---|
| 让"追加测试"做成了"整份覆盖"，丢了原有 6 个测试 | **"追加"与"替换"必须区分**；改完立刻 `pytest --collect-only -q` 核对数量 |
| `docs/migration-notes` 推送了但一直没开 PR | **推送 ≠ 提交**。分支推上去只是备份，不开 PR 就永远进不了 main |
| 协作者分支挂了两天没人动 | 新手最常见的误解就是"推上去等于提交了"，需要主动提醒开 PR |
| 多次"文件建错位置/名字" | 建完立刻列目录，比读报错猜快得多 |
| 一次改多个文件时漏改名 import | 改完先自检（grep 关键字），再跑测试 |

---

## 附：本文件收录的问题中，最值得在面试里讲的三个

1. **测试夹具不真实 vs 生产阈值**（D-3）
   > "测试红了，我第一反应不是改阈值，而是问'夹具真实吗'。
   > 把阈值从 25 降到 10 能让测试变绿，但扫描件检测就废了。"

2. **squash 语义带来的连锁反应**（B-2 / B-3）
   > "我们统一用 squash 合并，这带来两个必须记住的副作用：
   > 原始提交不再是 main 的祖先（所以 `branch -d` 会拒绝），
   > 且 PR 标题就是最终提交信息（所以标题必须符合规范）。"

3. **容器镜像是代码的快照**（C-5）
   > "前端报 404，路由明明写了。查下来是容器里跑的是三天前的镜像。
   > 后来我把'改代码即生效'（本地 uvicorn）和'交付形态验证'（重建镜像）分成两个明确动作。"
