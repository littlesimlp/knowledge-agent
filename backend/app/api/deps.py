"""路由层共享的依赖声明。

把"如何构造依赖"集中在一处，路由函数只声明类型。
测试时用 app.dependency_overrides 替换，生产代码零改动（和数据库 session 同一套思路）。
"""

from typing import Annotated

from fastapi import Depends

from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider

# 业务永远只看到 LLMProvider，看不到具体是哪家模型
LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]