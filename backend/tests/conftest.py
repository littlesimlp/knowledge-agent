"""pytest 全局配置与夹具。

三条关键设计：
1. 测试连 knowledge_test 库，绝不碰开发库
2. 每次测试跑在一个事务里，结束回滚 —— 测试之间完全隔离
3. 用 dependency_overrides 把应用的 get_session 换成测试 session
"""

import asyncio
from collections.abc import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app

TEST_DB_NAME = "knowledge_test"

# 把开发库 URL 的库名换成测试库名
_parts = urlsplit(settings.database_url)
TEST_DATABASE_URL = urlunsplit(_parts._replace(path=f"/{TEST_DB_NAME}"))


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> AsyncGenerator[None, None]:
    """整个测试会话开始前，重建测试库的表结构。

    这里用同步夹具 + asyncio.run，是为了绕开 pytest-asyncio
    在 session 级异步夹具上的事件循环作用域问题。
    """

    async def _run() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())
    yield


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """一个测试一个事务，测试结束回滚，表结构保留。"""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as s:
            yield s
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """带数据库覆盖的 HTTP 客户端。"""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()