CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prime_status BIT DEFAULT CAST(0 AS BIT),
    joined_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT NOT NULL PRIMARY KEY,
    balance BIGINT DEFAULT 0 CHECK (balance >= 0)
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
)

-- CREATE TABLE IF NOT EXISTS inventories (
--     user_id BIGINT NOT NULL,
--     item_id INTEGER NOT NULL CHECK (item_id > 1),
--     amount INTEGER NOT NULL DEFAULT 0 CHECK (amount > 0),
--     FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE CASCADE,
--     FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
--     UNIQUE (user_id, item_id)
-- );

-- CREATE TABLE IF NOT EXISTS tags (
--     guild_id BIGINT, -- Null if alias
--     user_id BIGINT NOT NULL,
--     tag_id TEXT NOT NULL PRIMARY KEY,
--     tag_name VARCHAR(32), -- Null if alias
--     tag_content TEXT, -- Null if alias
--     alias_to TEXT, -- Null if not alias, otherwise the ID of the tag it refers to
--     tag_uses INTEGER NOT NULL DEFAULT 0,
--     created_at TIMESTAMP NOT NULL DEFAULT NOW(),
--     FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
--     UNIQUE(guild_id, tag_name)
-- );