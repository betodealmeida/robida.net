DROP TABLE IF EXISTS entries;
CREATE TABLE entries(
    uuid TEXT PRIMARY KEY,
    author URI,
    location URI,
    content JSON,
    read BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    last_modified_at TIMESTAMP
);
CREATE INDEX idx_entries_author ON entries(author);
CREATE INDEX idx_entries_location ON entries(location);

DROP TABLE IF EXISTS documents;
CREATE VIRTUAL TABLE documents USING fts5(uuid, content);

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
    created_at TIMESTAMP
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
    created_at TIMESTAMP
);

DROP TABLE IF EXISTS websub_publisher;
CREATE TABLE websub_publisher (
    callback TEXT NOT NULL,
    topic TEXT NOT NULL,
    expires_at TIMESTAMP,
    secret TEXT,
    last_delivery_at TIMESTAMP,
    UNIQUE(callback, topic)
);

DROP TABLE IF EXISTS incoming_webmentions;
CREATE TABLE incoming_webmentions (
    uuid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    vouch TEXT,
    status TEXT NOT NULL,
    message TEXT,
    content TEXT,
    created_at TIMESTAMP,
    last_modified_at TIMESTAMP,
    UNIQUE(source, target)
);
CREATE INDEX idx_incoming_webmentions_source ON incoming_webmentions(source);
CREATE INDEX idx_incoming_webmentions_target ON incoming_webmentions(target);
CREATE INDEX idx_incoming_webmentions_status ON incoming_webmentions(status);

DROP TABLE IF EXISTS outgoing_webmentions;
CREATE TABLE outgoing_webmentions (
    uuid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    vouch TEXT,
    status TEXT NOT NULL,
    message TEXT,
    content TEXT,
    created_at TIMESTAMP,
    last_modified_at TIMESTAMP,
    UNIQUE(source, target)
);
CREATE INDEX idx_outgoing_webmentions_source ON outgoing_webmentions(source);
CREATE INDEX idx_outgoing_webmentions_target ON outgoing_webmentions(target);
CREATE INDEX idx_outgoing_webmentions_status ON outgoing_webmentions(status);

DROP TABLE IF EXISTS trusted_domains;
CREATE TABLE trusted_domains (
    domain TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    UNIQUE(domain)
);
