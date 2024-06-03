DROP TABLE IF EXISTS entries;
CREATE TABLE entries(
    uuid TEXT PRIMARY KEY,
    author URI,
    content JSON,
    read BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entries_h ON entries((content->>'$.type'));

DROP TABLE IF EXISTS oauth_authorization_codes;
CREATE TABLE oauth_authorization_codes(
    code TEXT PRIMARY KEY,
    client_id URI,
    redirect_uri URI,
    code_challenge TEXT,
    code_challenge_method TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
