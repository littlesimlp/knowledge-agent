"""add trigram search indexes

Revision ID: 0de511119ced
Revises: 8d1a0cbf84bd
Create Date: 2026-11-05 17:29:46.935232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0de511119ced'
down_revision: Union[str, Sequence[str], None] = '8d1a0cbf84bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 中文没有空格分词，simple 配置会把整段中文当成一个 token，
    # 所以检索用 ILIKE 子串；pg_trgm 让 GIN 索引能加速 `%...%` 查询。
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_knowledge_entries_title_trgm",
        "knowledge_entries",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_knowledge_entries_content_trgm",
        "knowledge_entries",
        ["content"],
        postgresql_using="gin",
        postgresql_ops={"content": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_entries_content_trgm", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_title_trgm", table_name="knowledge_entries")
    # 不 DROP EXTENSION：扩展可能被其它索引/对象使用。