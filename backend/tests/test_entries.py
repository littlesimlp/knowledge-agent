"""知识条目接口测试。"""

import uuid

from httpx import AsyncClient

from app.models.knowledge_entry import DEFAULT_WORKSPACE_ID


async def test_create_entry(client: AsyncClient) -> None:
    response = await client.post(
        "/api/entries",
        json={
            "title": "测试标题",
            "content": "测试正文内容",
            "category": "测试",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "测试标题"
    assert body["category"] == "测试"
    # 断言是合法 UUID，而不是硬编码某个值
    assert uuid.UUID(body["id"])
    # 服务端自动填了 workspace_id
    assert body["workspace_id"] == str(DEFAULT_WORKSPACE_ID)
    # 数据库端生成的时间戳必须有值
    assert body["created_at"]
    assert body["updated_at"]


async def test_list_returns_created_entry(client: AsyncClient) -> None:
    await client.post(
        "/api/entries",
        json={"title": "列表测试", "content": "内容"},
    )

    response = await client.get("/api/entries")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "列表测试" in titles


async def test_get_missing_entry_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/entries/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_patch_only_updates_given_fields(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/entries",
            json={
                "title": "原标题",
                "content": "原正文",
                "summary": "原摘要",
                "category": "原分类",
            },
        )
    ).json()

    response = await client.patch(
        f"/api/entries/{created['id']}",
        json={"category": "新分类"},
    )

    assert response.status_code == 200
    body = response.json()
    # 只有 category 变了，其它字段必须原样保留
    assert body["category"] == "新分类"
    assert body["title"] == "原标题"
    assert body["content"] == "原正文"
    assert body["summary"] == "原摘要"


async def test_delete_entry(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/entries",
            json={"title": "待删除", "content": "内容"},
        )
    ).json()

    delete_response = await client.delete(f"/api/entries/{created['id']}")
    assert delete_response.status_code == 204

    # 删完再查应该 404
    assert (await client.get(f"/api/entries/{created['id']}")).status_code == 404


async def test_tests_are_isolated(client: AsyncClient) -> None:
    """这个测试依赖上一条测试什么都没留下。

    如果事务回滚失效，前面几个测试创建的数据会泄漏到这里。
    """
    response = await client.get("/api/entries")
    assert response.json() == []