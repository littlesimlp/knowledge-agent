"""Knowledge Agent API 入口。"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import entries, imports

app = FastAPI(title="Knowledge Agent API", version="0.1.0")

app.include_router(entries.router)
app.include_router(imports.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """访问根路径时跳到交互式文档。

    没有这个路由，浏览器打开 http://127.0.0.1:8000 会看到 404，
    第一次访问的人会以为服务没起来。
    """
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    """存活探针：不查数据库、不调模型，只证明进程活着。"""
    return {"status": "ok"}