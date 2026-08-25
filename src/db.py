import sqlite_utils

from migrations import migrations


def get_db(path="db.sqlite3"):
	db = sqlite_utils.Database(path)
	migrations.apply(db)
	return db


db = get_db()