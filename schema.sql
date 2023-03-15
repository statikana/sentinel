-- DROP TABLE IF EXISTS guilds CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS blacklist CASCADE;
-- DROP TABLE IF EXISTS tags CASCADE;
-- DROP TABLE IF EXISTS tag_meta CASCADE;

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prime_status BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP DEFAULT NOW(),
    prefix VARCHAR(16) DEFAULT '>>'
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT NOT NULL PRIMARY KEY,
    balance BIGINT DEFAULT 0 CHECK (balance >= 0)
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tag_meta (
    tag_id BIGINT NOT NULL PRIMARY KEY,
    tag_name VARCHAR(32) NOT NULL,
    owner_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    alias_to BIGINT DEFAULT NULL,
    FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (guild_id) REFERENCES guilds (guild_id) ON DELETE CASCADE,
    UNIQUE (guild_id, tag_name)
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id BIGINT NOT NULL PRIMARY KEY,
    tag_content TEXT NOT NULL CHECK (LENGTH(tag_content) <= 2000),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    tag_uses INTEGER DEFAULT 0 CHECK (tag_uses >= 0),
    FOREIGN KEY (tag_id) REFERENCES tag_meta (tag_id) ON DELETE CASCADE
)