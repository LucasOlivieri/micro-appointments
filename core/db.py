import sqlite_utils

from core.migrations import migrations, sync_config_to_db


def get_db(path="db.sqlite3"):
    db = sqlite_utils.Database(path)
    migrations.apply(db)
    sync_config_to_db(db)
    return db


db = get_db()
