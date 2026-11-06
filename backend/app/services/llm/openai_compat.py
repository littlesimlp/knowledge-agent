"""OpenAI 兼容协议的实现。

DeepSeek 和 SiliconFlow 都用这套协议，差异只有 base_url 和 model
（D-021：一个实现 + 两套配置，而不是两个适配器）。
"""

import json
import logging
from collections.abc import Sequence

import httpx

from app.services.llm.base import AnswerDraft, EntrySuggestion, LLMError

logger = logging.getLogger(__name__)

# 数据库对标题/分类有长度限制，提前截断，避免"建议能生成但保存失败"
_TITLE_MAX = 200
_CATEGORY_MAX = 100
_KEYWORDS_MAX = 8
_ANSWER_MAX = 4000

_SYSTEM_PROMPT = """你是技术知识库的整理助手。用户会给你一段技术资料，你要提取元信息。

只输出一个 JSON 对象，不要有任何解释文字，格式严格如下：
{
  "title": "20 字以内的中文标题",
  "summary": "50 字以内的中文摘要",
  "keywords": ["关键词1", "关键词2"],
  "category": "一个简短的中文分类名"
}

要求：
- 全部使用中文
- keywords 最多 5 个，每个不超过 10 个字
- 无法判断的字段填 null
- 不要输出 JSON 以外的任何内容"""

_ANSWER_SYSTEM_PROMPT = """你是个人知识库的问答助手。只能依据用户给出的编号资料回答，
不能使用资料以外的知识。

输出一个 JSON 对象，不要有任何解释文字，格式严格如下：
{
  "answer": "中文回答",
  "citations": [1, 2]
}

要求：
- citations 只能包含你实际依据的资料编号（整数），没有依据时填空数组
- 资料不足以回答时，answer 写"资料中未提及相关内容"，citations 为空
- 不要编造资料编号，不要引用不存在的编号
- 不要输出 JSON 以外的任何内容"""


def _load_json_object(raw: str) -> dict[str, object]:
    """把模型返回的原始文本提取成 JSON 对象。

    模型返回的内容通常不干净：可能被 ```json 包裹、前后有解释文字。
    提取失败一律抛 LLMError。
    """
    text = (raw or "").strip()
    if not text:
        raise LLMError("模型返回了空内容")

    # 容忍 ```json ... ``` 包裹
    if text.startswith("```"):
        text = text.split("```")[1] if len(text.split("```")) > 1 else text
        if text.startswith("json"):
            text = text[len("json") :]
        text = text.strip()

    # 容忍前后有解释文字：截取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError(f"模型返回的内容里找不到 JSON 对象：{text[:120]}")
    text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"模型返回的 JSON 无法解析：{exc}") from exc

    if not isinstance(data, dict):
        raise LLMError("模型返回的 JSON 不是对象")
    return data


def parse_suggestion(raw: str) -> EntrySuggestion:
    """把模型返回的原始文本解析成 EntrySuggestion。"""
    data = _load_json_object(raw)
    return EntrySuggestion(
        title=_clean_str(data.get("title"), _TITLE_MAX),
        summary=_clean_str(data.get("summary")),
        keywords=_clean_keywords(data.get("keywords")),
        category=_clean_str(data.get("category"), _CATEGORY_MAX),
    )


def parse_answer(raw: str) -> AnswerDraft:
    """解析问答结果：回答文本 + 引用编号。

    这里只做"类型收敛"（非整数编号丢弃、去重），不校验编号范围——
    "编号是否在候选集内"属于业务规则，放在 service 层。
    """
    data = _load_json_object(raw)
    answer = _clean_str(data.get("answer"), _ANSWER_MAX)
    if answer is None:
        raise LLMError("模型没有给出回答内容")

    numbers: list[int] = []
    raw_numbers = data.get("citations")
    if isinstance(raw_numbers, list):
        for item in raw_numbers:
            number: int | None = None
            if isinstance(item, bool):
                number = None
            elif isinstance(item, int):
                number = item
            elif isinstance(item, str) and item.strip().isdigit():
                number = int(item.strip())
            if number is not None and number not in numbers:
                numbers.append(number)

    return AnswerDraft(answer=answer, citation_numbers=tuple(numbers))


def _clean_str(value: object, max_length: int | None = None) -> str | None:
    """把任意值收敛成"非空字符串或 None"。"""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if max_length is not None:
        cleaned = cleaned[:max_length]
    return cleaned or None


def _clean_keywords(value: object) -> tuple[str, ...]:
    """关键词必须是字符串数组；其它形态一律丢弃，不报错。"""
    if not isinstance(value, list):
        return ()

    result: list[str] = []
    for item in value:
        cleaned = _clean_str(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= _KEYWORDS_MAX:
            break
    return tuple(result)


class OpenAICompatProvider:
    """通过 OpenAI 兼容的 /chat/completions 完成建议与问答。"""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_input_chars: int,
    ) -> None:
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_input_chars = max_input_chars

    async def suggest_entry(self, text: str) -> EntrySuggestion:
        content = await self._chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[: self._max_input_chars]},
            ]
        )
        return parse_suggestion(content)

    async def answer(self, question: str, contexts: Sequence[str]) -> AnswerDraft:
        question_part = f"\n\n问题：{question}"
        materials = "\n\n".join(contexts)
        # 问题必须保留；只截断资料部分
        budget = max(
            0,
            self._max_input_chars - len(_ANSWER_SYSTEM_PROMPT) - len(question_part),
        )
        content = await self._chat(
            [
                {"role": "system", "content": _ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": f"资料：\n{materials[:budget]}{question_part}"},
            ]
        )
        return parse_answer(content)

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        if not self._api_key:
            raise LLMError(f"缺少 API key：请在 .env 设置 LLM_API_KEY（provider={self.name}）")
        if not self._model:
            raise LLMError("缺少模型名：请在 .env 设置 LLM_MODEL")

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
            # 两家都支持这个参数，能显著降低"返回废话"的概率
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMError(f"模型调用超时（>{self._timeout:.0f} 秒）") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"模型调用失败：{exc}") from exc

        if response.status_code >= 400:
            # 注意：不打印 api_key，也不打印整个响应头
            raise LLMError(
                f"模型服务返回 {response.status_code}：{response.text[:200]}"
            )

        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError("模型响应结构不符合 OpenAI 协议") from exc