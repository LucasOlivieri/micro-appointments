CREATE TABLE IF NOT EXISTS customer (
    id TEXT PRIMARY KEY NOT NULL,
    phone TEXT UNIQUE,
    name TEXT,
    info TEXT
);

ALTER TABLE blocked_times ADD COLUMN "customer" TEXT;
