DROP TABLE IF EXISTS guild_data CASCADE;
DROP TABLE IF EXISTS guild_configs CASCADE;
DROP TABLE IF EXISTS user_data CASCADE;
DROP TABLE IF EXISTS user_configs CASCADE;
DROP TABLE IF EXISTS blacklist CASCADE;
DROP TABLE IF EXISTS tag_data CASCADE;
DROP TABLE IF EXISTS tag_meta CASCADE;

CREATE TABLE IF NOT EXISTS guild_data (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prime_status BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMP DEFAULT NOW(),
    prefix VARCHAR(16) DEFAULT '>>'
);

CREATE TABLE IF NOT EXISTS guild_configs (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prefix VARCHAR(16) DEFAULT '>>',
    autoresponse_functions TEXT[] DEFAULT ARRAY[]::TEXT[],
    autoresponse_enabled BOOLEAN DEFAULT TRUE,
    allow_autoresponse_immunity BOOLEAN DEFAULT TRUE,
    welcome_channel_id BIGINT DEFAULT NULL,
    welcome_message_title TEXT DEFAULT NULL,
    welcome_message_body TEXT DEFAULT NULL,
    welcome_message_enabled BOOLEAN DEFAULT TRUE,
    leave_channel_id BIGINT DEFAULT NULL,
    leave_message_title TEXT DEFAULT NULL,
    leave_message_body TEXT DEFAULT NULL,
    leave_message_enabled BOOLEAN DEFAULT TRUE,
    modlog_channel_id BIGINT DEFAULT NULL,
    modlog_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (guild_id) REFERENCES guild_data (guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_data (
    user_id BIGINT NOT NULL PRIMARY KEY,
    balance BIGINT DEFAULT 0 CHECK (balance >= 0),
    tokens BIGINT DEFAULT 0 CHECK (tokens >= 0),
    next_hourly TIMESTAMP DEFAULT NOW(),
    next_daily TIMESTAMP DEFAULT NOW(),
    next_weekly TIMESTAMP DEFAULT NOW(),
    next_monthly TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_configs (
    user_id BIGINT NOT NULL PRIMARY KEY,
    autoresponse_immune BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
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
    FOREIGN KEY (guild_id) REFERENCES guild_data (guild_id) ON DELETE CASCADE,
    UNIQUE (guild_id, tag_name)
);

CREATE TABLE IF NOT EXISTS tag_data (
    tag_id BIGINT NOT NULL PRIMARY KEY,
    tag_content TEXT NOT NULL CHECK (LENGTH(tag_content) <= 2000),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    tag_uses INTEGER DEFAULT 0 CHECK (tag_uses >= 0),
    FOREIGN KEY (tag_id) REFERENCES tag_meta (tag_id) ON DELETE CASCADE
)