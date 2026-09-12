CREATE TABLE blocked_times_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    appointment_type TEXT,
    customer TEXT,
    google_event_id TEXT
);
INSERT INTO blocked_times_new SELECT * FROM blocked_times;
DROP TABLE blocked_times;
ALTER TABLE blocked_times_new RENAME TO blocked_times;
