"""上传文件落盘。

安全规则：**永远不用用户提供的文件名拼磁盘路径。**
用户可能上传 `../../config.py`（路径穿越）或 `con.md`（Windows 保留名）。
我们只取后缀，文件名用 uuid 重新生成。
"""

import uuid
from pathlib import Path

from app.core.config import settings

UPLOAD_SUBDIR = "uploads"


def save_upload(data: bytes, original_name: str) -> Path:
    """把字节写到 data_dir/uploads/<uuid><后缀>，返回绝对路径。"""
    suffix = Path(original_name).suffix.lower()
    uploads = settings.data_dir / UPLOAD_SUBDIR
    uploads.mkdir(parents=True, exist_ok=True)

    target = uploads / f"{uuid.uuid4().hex}{suffix}"
    target.write_bytes(data)
    return target


def relative_path(path: Path) -> str:
    """转成相对 data_dir 的 POSIX 路径。

    存相对路径而不是绝对路径：本机是 D:\...\data，容器里是 /app/data，
    同一个文件在两处路径不同，但相对路径一致。
    """
    return path.relative_to(settings.data_dir).as_posix()