"""知识来源的响应契约。

注意：**故意不暴露 extracted_text**。
原文可能有几百 KB，放进每次响应里会让响应体爆炸；
需要看全文时用单独的详情接口（M3 再提供）。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeSourceRead(BaseModel):
    """返回给客户端的来源信息（不含全文）。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    source_type: str
    source_name: str
    source_url: str | None
    file_path: str | None
    source_excerpt: str | None
    created_at: datetime