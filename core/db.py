import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None
_query_cache: dict[str, str] = {}


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


def load_queries() -> None:
    """Walk core/queries/ recursively, read every .sql file, cache by subdir/stem."""
    queries_dir = Path(__file__).resolve().parent / "queries"
    if not queries_dir.exists():
        logger.warning("Queries directory not found: %s", queries_dir)
        return
    for sql_file in queries_dir.rglob("*.sql"):
        relative = sql_file.relative_to(queries_dir)
        key = str(relative.with_suffix("")).replace("\\", "/")
        _query_cache[key] = sql_file.read_text(encoding="utf-8")
    logger.info("Loaded %d queries into cache", len(_query_cache))


def get_query(name: str) -> str:
    try:
        return _query_cache[name]
    except KeyError:
        raise KeyError(f"Query not found: {name}") from None


async def init_db(path: str | Path = "db.sqlite3", sync_config: bool = True) -> None:
    global _db

    # Lazy import to avoid circular dependency (core.migrations imports get_db)
    from core.migrations import apply_migrations, sync_config_to_db

    normalized_path = str(Path(path))

    if _db is not None:
        await close_db()

    _db = await aiosqlite.connect(normalized_path)
    _db.row_factory = aiosqlite.Row

    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    load_queries()
    await apply_migrations()
    if sync_config:
        await sync_config_to_db()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
