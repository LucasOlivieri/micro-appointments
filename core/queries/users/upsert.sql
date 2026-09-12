INSERT INTO users (id, name, email, timezone, message, system_prompt)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    name = excluded.name,
    email = excluded.email,
    timezone = excluded.timezone,
    message = excluded.message,
    system_prompt = excluded.system_prompt
