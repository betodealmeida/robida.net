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
