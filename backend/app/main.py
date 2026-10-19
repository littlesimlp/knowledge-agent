"""Knowledge Agent API 入口。"""

from fastapi import FastAPI

app = FastAPI(title="Knowledge Agent API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """存活探针：不查数据库、不调模型，只证明进程活着。"""
    return {"status": "ok"}
