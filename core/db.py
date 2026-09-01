from pathlib import Path

from tortoise import Tortoise

from core.migrations import apply_migrations, sync_config_to_db


async def init_db(path: str | Path = "db.sqlite3") -> None:
    normalized_path = str(Path(path))

    if Tortoise._inited:  # type: ignore[attr-defined]
        await close_db()

    await Tortoise.init(
        db_url=f"sqlite://{normalized_path}",
        modules={"models": ["core.models"]},
        _enable_global_fallback=True,
    )
    await apply_migrations()
    await sync_config_to_db()


async def close_db() -> None:
    if Tortoise._inited:  # type: ignore[attr-defined]
        await Tortoise.close_connections()
