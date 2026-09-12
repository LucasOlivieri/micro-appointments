INSERT INTO customer (id, phone, name, info) VALUES (?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    phone = excluded.phone,
    name = excluded.name,
    info = excluded.info
