"""M5-1b: 一键备份 + 恢复演练。

在 backend/ 目录下运行：
    uv run python scripts/drill.py
    uv run python scripts/drill.py --keep-restore

流程：pg_dump -> 打包 uploads -> 恢复到 knowledge_restore -> 校验行数与 SHA256。
不修改开发库 knowledge；失败返回非零退出码。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = REPO_ROOT / "backend" / "data" / "uploads"
BACKUPS_DIR = REPO_ROOT / "backups"

DB_SERVICE = "db"
DB_USER = "knowledge"
DB_NAME = "knowledge"
RESTORE_DB = "knowledge_restore"
CONTAINER_DUMP = "/tmp/drill-knowledge.dump"

COUNT_SQL = (
    "select (select count(*) from knowledge_entries) || ',' || "
    "(select count(*) from knowledge_sources) || ',' || "
    "(select count(*) from knowledge_entry_sources);"
)


def compose(*args: str) -> list[str]:
    return ["docker", "compose", *args]


def run(args: list[str]) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def psql(db: str, sql: str) -> str:
    result = subprocess.run(
        compose(
            "exec", "-T", DB_SERVICE,
            "psql", "-U", DB_USER, "-d", db, "-Atc", sql,
        ),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_manifest(root: Path) -> dict[str, str]:
    """返回 {相对路径: sha256}；目录不存在时返回空字典。"""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def pack_uploads(target: Path) -> None:
    with tarfile.open(target, "w:gz") as archive:
        archive.add(UPLOADS_DIR, arcname="uploads")


def unpack_uploads(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(destination, filter="data")


def human_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.2f} MB"


def dump_database(target: Path) -> None:
    run(
        compose(
            "exec", "-T", DB_SERVICE,
            "pg_dump", "-U", DB_USER, "-d", DB_NAME, "-Fc", "-f", CONTAINER_DUMP,
        )
    )
    run(compose("cp", f"{DB_SERVICE}:{CONTAINER_DUMP}", str(target)))


def restore_database(dump: Path) -> None:
    psql(DB_NAME, f"drop database if exists {RESTORE_DB} with (force);")
    psql(DB_NAME, f"create database {RESTORE_DB};")
    run(compose("cp", str(dump), f"{DB_SERVICE}:{CONTAINER_DUMP}"))
    run(
        compose(
            "exec", "-T", DB_SERVICE,
            "pg_restore", "-U", DB_USER, "-d", RESTORE_DB,
            "--no-owner", "--exit-on-error", CONTAINER_DUMP,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="备份 + 恢复演练")
    parser.add_argument(
        "--keep-restore",
        action="store_true",
        help="演练成功后也保留 knowledge_restore 库",
    )
    args = parser.parse_args()

    if not UPLOADS_DIR.exists():
        print(f"uploads dir not found: {UPLOADS_DIR}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUPS_DIR / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    dump_path = backup_dir / "knowledge.dump"
    uploads_tar = backup_dir / "uploads.tar.gz"
    restore_dir = backup_dir / "restore-data"

    keep = args.keep_restore
    failures: list[str] = []
    source_counts = ""
    restore_counts = ""
    source_manifest: dict[str, str] = {}
    restored_manifest: dict[str, str] = {}
    backup_seconds = 0.0
    restore_seconds = 0.0

    try:
        started = time.perf_counter()
        dump_database(dump_path)
        pack_uploads(uploads_tar)
        source_manifest = tree_manifest(UPLOADS_DIR)
        (backup_dir / "uploads-sha256.json").write_text(
            json.dumps(source_manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        backup_seconds = time.perf_counter() - started

        started = time.perf_counter()
        restore_database(dump_path)
        unpack_uploads(uploads_tar, restore_dir)
        restore_seconds = time.perf_counter() - started

        source_counts = psql(DB_NAME, COUNT_SQL)
        restore_counts = psql(RESTORE_DB, COUNT_SQL)
        if source_counts != restore_counts:
            failures.append(
                f"row counts differ: source={source_counts} restore={restore_counts}"
            )

        restored_manifest = tree_manifest(restore_dir / "uploads")
        if source_manifest != restored_manifest:
            missing = sorted(set(source_manifest) - set(restored_manifest))
            extra = sorted(set(restored_manifest) - set(source_manifest))
            changed = sorted(
                name
                for name in set(source_manifest) & set(restored_manifest)
                if source_manifest[name] != restored_manifest[name]
            )
            failures.append(
                f"upload files differ: missing={missing} extra={extra} changed={changed}"
            )
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
        keep = True
    finally:
        subprocess.run(
            compose("exec", "-T", DB_SERVICE, "rm", "-f", CONTAINER_DUMP),
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if not keep:
            subprocess.run(
                compose(
                    "exec", "-T", DB_SERVICE,
                    "psql", "-U", DB_USER, "-d", DB_NAME,
                    "-c", f"drop database if exists {RESTORE_DB} with (force);",
                ),
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

    dump_size = dump_path.stat().st_size if dump_path.exists() else 0
    tar_size = uploads_tar.stat().st_size if uploads_tar.exists() else 0
    print()
    print(
        f"backup : {backup_dir}  "
        f"dump={human_size(dump_size)} uploads={human_size(tar_size)} "
        f"in {backup_seconds:.1f}s"
    )
    print(f"restore: {restore_seconds:.1f}s  dir={restore_dir}")
    print(f"counts : {source_counts} vs {restore_counts}")
    print(f"files  : {len(source_manifest)} vs {len(restored_manifest)} (sha256)")

    if failures:
        print("result : FAIL")
        for failure in failures:
            print(f"  - {failure}")
        if keep:
            print("restore db kept for debugging")
        return 1

    print("result : PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())