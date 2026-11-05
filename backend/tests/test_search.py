"""检索接口测试（M4-1）。

重点覆盖：中文子串（分词做不到的）、LIKE 通配符转义、关键词过滤。
"""

from httpx import AsyncClient


async def _create(
    client: AsyncClient,
    title: str,
    content: str,
    *,
    keywords: list[str] | None = None,
) -> dict:
    response = await client.post(
        "/api/entries",
        json={"title": title, "content": content, "keywords": keywords or []},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_matches_title_and_content(client: AsyncClient) -> None:
    await _create(client, "Docker 网络模式", "bridge / host / none")
    await _create(client, "无关条目", "这里提到 docker compose")

    response = await client.get("/api/search", params={"q": "docker"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # 标题命中排在正文命中前面
    assert body[0]["entry"]["title"] == "Docker 网络模式"


async def test_chinese_substring_matches(client: AsyncClient) -> None:
    """simple 配置搜「数据库」匹配不到「数据库连接池」，子串可以。"""
    await _create(client, "数据库连接池", "连接池大小与超时配置")

    response = await client.get("/api/search", params={"q": "连接池"})

    assert response.status_code == 200
    assert [hit["entry"]["title"] for hit in response.json()] == ["数据库连接池"]


async def test_case_insensitive(client: AsyncClient) -> None:
    await _create(client, "Docker 入门", "容器基础")

    response = await client.get("/api/search", params={"q": "DOCKER"})

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_keyword_filter(client: AsyncClient) -> None:
    await _create(client, "带关键词", "docker 网络", keywords=["docker"])
    await _create(client, "不带关键词", "docker 网络")

    response = await client.get(
        "/api/search", params={"q": "docker", "keyword": "docker"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["entry"]["title"] == "带关键词"


async def test_wildcard_is_escaped(client: AsyncClient) -> None:
    """用户输入 `%` 不能变成“匹配全部”。"""
    await _create(client, "进度说明", "完成了 100% 的测试")
    await _create(client, "另一条", "满分 100 分，但与百分号无关")

    response = await client.get("/api/search", params={"q": "100%"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["entry"]["title"] == "进度说明"


async def test_no_match_returns_empty(client: AsyncClient) -> None:
    await _create(client, "Docker", "容器")

    response = await client.get("/api/search", params={"q": "kubernetes"})

    assert response.status_code == 200
    assert response.json() == []


async def test_limit(client: AsyncClient) -> None:
    for index in range(3):
        await _create(client, f"docker 笔记 {index}", "容器")

    response = await client.get("/api/search", params={"q": "docker", "limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_blank_query_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/search", params={"q": "   "})
    assert response.status_code == 422


async def test_snippet_contains_query(client: AsyncClient) -> None:
    content = "前面很多内容 " + "填充 " * 30 + "关键结论在这里 " + "后面 " * 30
    await _create(client, "长文", content)

    response = await client.get("/api/search", params={"q": "关键结论"})

    body = response.json()
    assert len(body) == 1
    assert "关键结论" in body[0]["snippet"]