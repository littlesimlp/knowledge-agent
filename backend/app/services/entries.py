"""知识条目的业务逻辑。

D-020：删除条目时，连带删除已无任何条目引用的来源记录与磁盘文件。
"""

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge_entry import KnowledgeEntry
from app.models.knowledge_source import KnowledgeEntrySource, KnowledgeSource

logger = logging.getLogger(__name__)


async def delete_entry_cascade(
    session: AsyncSession,
    entry: KnowledgeEntry,
) -> list[Path]:
    """删除条目，并连带删除因此变成孤儿的来源。

    返回"需要在事务提交后删除"的磁盘文件路径。
    **不在本函数里删文件**——文件系统没有事务，必须等数据库改动落定再动文件。
    """
    # 1. 这条条目关联了哪些来源
    source_ids = list(
        (
            await session.execute(
                select(KnowledgeEntrySource.source_id).where(
                    KnowledgeEntrySource.entry_id == entry.id
                )
            )
        ).scalars()
    )

    # 2. 删除条目；关联行由数据库的 ON DELETE CASCADE 清理
    await session.delete(entry)
    await session.flush()

    # 3. 逐个检查来源是否还有别的条目在用
    orphan_files: list[Path] = []
    for source_id in source_ids:
        remaining = await session.scalar(
            select(func.count())
            .select_from(KnowledgeEntrySource)
            .where(KnowledgeEntrySource.source_id == source_id)
        )
        if remaining:
            # 还被别的条目引用（多对多），保留来源
            continue

        source = await session.get(KnowledgeSource, source_id)
        if source is None:
            continue

        if source.file_path:
            path = _resolve_upload_path(source.file_path)
            if path is not None:
                orphan_files.append(path)

        await session.delete(source)

    await session.commit()
    return orphan_files


def _resolve_upload_path(relative: str) -> Path | None:
    """把数据库里的相对路径解析成 data_dir 内的绝对路径。

    删除文件不可逆，所以必须确认解析后的路径仍在 data_dir 之内。
    否则数据库里一个被篡改的 file_path（如 `../../config.py`）
    就能删掉磁盘上任意文件。
    """
    data_dir = settings.data_dir.resolve()
    candidate = (data_dir / relative).resolve()

    if not candidate.is_relative_to(data_dir):
        logger.warning("拒绝删除 data_dir 之外的路径：%s", candidate)
        return None
    return candidate


def remove_files(paths: list[Path]) -> list[str]:
    """事务提交后执行：删除磁盘文件。

    失败只记日志、不抛异常——数据库记录已经删了，此时因为文件删不掉
    而返回 500，只会让用户以为删除失败、反复重试。
    """
    failures: list[str] = []
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(f"{path}: {exc}")

    if failures:
        logger.warning("来源记录已删除，但文件删除失败：%s", "; ".join(failures))
    return failures