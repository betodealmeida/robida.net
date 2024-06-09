DROP TABLE IF EXISTS entries;
CREATE TABLE entries(
    uuid TEXT PRIMARY KEY,
    author URI,
    location URI,
    content JSON,
    read BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entries_author ON entries((author));
CREATE INDEX idx_entries_location ON entries((location));
CREATE INDEX idx_entries_in_reply_to ON entries((content->>'$.properties.in-reply-to[0]'));

DROP TABLE IF EXISTS oauth_authorization_codes;
CREATE TABLE oauth_authorization_codes(
    code TEXT PRIMARY KEY,
    client_id URI,
    redirect_uri URI,
    scope TEXT,
    code_challenge TEXT,
    code_challenge_method TEXT,
    used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS oauth_tokens;
CREATE TABLE oauth_tokens (
    client_id TEXT,
    token_type TEXT,
    access_token TEXT PRIMARY KEY,
    refresh_token TEXT,
    scope TEXT,
    expires_at TIMESTAMP,
    last_refresh_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS websub_publisher;
CREATE TABLE websub_publisher (
    callback TEXT NOT NULL,
    topic TEXT NOT NULL,
    expires_at TIMESTAMP,
    secret TEXT,
    last_delivery_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(callback, topic)
);
