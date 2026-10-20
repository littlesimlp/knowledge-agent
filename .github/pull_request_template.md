## 做了什么

<!-- 一句话说明这个 PR 的目的。例：新增知识条目的增删改查接口 -->

## 为什么

<!-- 关联的里程碑或问题。例：M1-3，见 docs/handoff/00-project-state.md -->

## 怎么验证

<!-- 评审者照着做就能确认。写具体命令和预期输出 -->

```bash
# 例：
# docker compose up -d
# curl http://127.0.0.1:8000/health
# → {"status":"ok"}
```

## 自检清单

- [ ] `cd backend && uv run ruff check .` 通过
- [ ] `cd backend && uv run python -m pytest -q` 通过
- [ ] `docker compose up -d` 后 `curl http://127.0.0.1:8000/health` 返回 `{"status":"ok"}`
- [ ] 没有提交 `.env`、密钥或真实数据
- [ ] 已同步 `main` 最新代码（`git pull --rebase`）

## 影响范围

- [ ] 仅文档
- [ ] 后端代码
- [ ] 数据库结构（**已附带 Alembic 迁移**）
- [ ] Docker / CI 配置
- [ ] 环境变量（**已同步更新 `.env.example`**）

## 备注 / 截图

<!-- 可选：接口返回示例、日志片段、设计取舍说明 -->
