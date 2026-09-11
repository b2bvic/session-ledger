
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA auto_vacuum = INCREMENTAL;

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY,
    session_uuid    TEXT NOT NULL,
    source          TEXT NOT NULL,
    project_path    TEXT,
    jsonl_path      TEXT,
    vault_file      TEXT,

    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    duration_ms     INTEGER,

    primary_domain  TEXT,
    domains         TEXT,
    purpose         TEXT,
    tags            TEXT,
    summary         TEXT,

    primary_model   TEXT,
    models_used     TEXT,
    claude_version  TEXT,

    total_input_tokens      INTEGER DEFAULT 0,
    total_output_tokens     INTEGER DEFAULT 0,
    total_cache_create      INTEGER DEFAULT 0,
    total_cache_read        INTEGER DEFAULT 0,
    estimated_cost_usd      REAL DEFAULT 0.0,

    message_count       INTEGER DEFAULT 0,
    user_message_count  INTEGER DEFAULT 0,
    assistant_turn_count INTEGER DEFAULT 0,
    tool_use_count      INTEGER DEFAULT 0,
    files_read_count    INTEGER DEFAULT 0,
    files_written_count INTEGER DEFAULT 0,
    files_edited_count  INTEGER DEFAULT 0,
    compact_count       INTEGER DEFAULT 0,

    subagent_count  INTEGER DEFAULT 0,
    first_prompt    TEXT,

    is_harvested    INTEGER DEFAULT 0 CHECK (is_harvested IN (0, 1)),
    harvest_version INTEGER DEFAULT 1,
    harvested_at    TEXT,
    raw_line_count  INTEGER DEFAULT 0,

    concurrency_group_id INTEGER,

    UNIQUE(session_uuid, source)
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    uuid            TEXT,
    parent_uuid     TEXT,
    timestamp       TEXT NOT NULL,

    role            TEXT NOT NULL CHECK (role IN (
                        'user', 'assistant', 'system', 'tool_result'
                    )),
    message_type    TEXT,
    subtype         TEXT,

    content_text    TEXT,
    content_json    TEXT,
    raw_json        TEXT,

    model           TEXT,
    request_id      TEXT,
    stop_reason     TEXT,

    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cache_create_tokens INTEGER,
    cache_read_tokens   INTEGER,

    is_sidechain    INTEGER DEFAULT 0 CHECK (is_sidechain IN (0, 1)),
    is_compact_summary INTEGER DEFAULT 0 CHECK (is_compact_summary IN (0, 1)),

    sequence_num    INTEGER NOT NULL,

    agent_id        TEXT,
    agent_slug      TEXT
);

CREATE TABLE IF NOT EXISTS tool_uses (
    id              INTEGER PRIMARY KEY,
    message_id      INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tool_use_id     TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    input_json      TEXT,
    timestamp       TEXT NOT NULL,

    file_path       TEXT,
    command         TEXT,
    pattern         TEXT,
    description     TEXT,

    result_message_id INTEGER REFERENCES messages(id),
    result_text     TEXT,
    is_error        INTEGER DEFAULT 0 CHECK (is_error IN (0, 1)),
    duration_ms     INTEGER
);

CREATE TABLE IF NOT EXISTS file_operations (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    operation       TEXT NOT NULL CHECK (operation IN ('read', 'write', 'edit', 'glob', 'grep')),
    first_at        TEXT NOT NULL,
    last_at         TEXT NOT NULL,
    operation_count INTEGER DEFAULT 1,
    vault_relative  TEXT,
    domain          TEXT,

    UNIQUE(session_id, file_path, operation)
);

CREATE TABLE IF NOT EXISTS compactions (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id      INTEGER REFERENCES messages(id),
    pre_tokens      INTEGER,
    summary_text    TEXT,
    timestamp       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subagents (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id        TEXT NOT NULL,
    slug            TEXT,
    model           TEXT,
    jsonl_path      TEXT,
    message_count   INTEGER DEFAULT 0,
    tool_use_count  INTEGER DEFAULT 0,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    started_at      TEXT,
    ended_at        TEXT,

    UNIQUE(session_id, agent_id)
);

CREATE TABLE IF NOT EXISTS concurrency_groups (
    id              INTEGER PRIMARY KEY,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    session_count   INTEGER DEFAULT 0,
    domains         TEXT,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS harvest_log (
    id              INTEGER PRIMARY KEY,
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    file_size       INTEGER,
    file_mtime      TEXT,
    session_uuid    TEXT,
    harvested_at    TEXT NOT NULL,
    line_count      INTEGER,
    message_count   INTEGER,
    status          TEXT DEFAULT 'complete' CHECK (status IN ('complete', 'partial', 'error')),
    error_text      TEXT,
    harvest_version INTEGER DEFAULT 1,

    UNIQUE(file_path, file_hash)
);

CREATE TABLE IF NOT EXISTS model_pricing (
    id              INTEGER PRIMARY KEY,
    model_name      TEXT NOT NULL,
    effective_date  TEXT NOT NULL,
    input_per_mtok  REAL NOT NULL,
    output_per_mtok REAL NOT NULL,
    cache_create_per_mtok REAL DEFAULT 0,
    cache_read_per_mtok REAL DEFAULT 0,
    notes           TEXT,

    UNIQUE(model_name, effective_date)
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_uuid ON sessions(session_uuid);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_domain ON sessions(primary_domain);
CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
CREATE INDEX IF NOT EXISTS idx_sessions_group ON sessions(concurrency_group_id);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence_num);
CREATE INDEX IF NOT EXISTS idx_messages_uuid ON messages(uuid);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(session_id, role);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_model ON messages(model);

CREATE INDEX IF NOT EXISTS idx_tools_session ON tool_uses(session_id);
CREATE INDEX IF NOT EXISTS idx_tools_name ON tool_uses(tool_name);
CREATE INDEX IF NOT EXISTS idx_tools_file ON tool_uses(file_path);
CREATE INDEX IF NOT EXISTS idx_tools_message ON tool_uses(message_id);

CREATE INDEX IF NOT EXISTS idx_fileops_session ON file_operations(session_id);
CREATE INDEX IF NOT EXISTS idx_fileops_path ON file_operations(file_path);
CREATE INDEX IF NOT EXISTS idx_fileops_domain ON file_operations(domain);

CREATE INDEX IF NOT EXISTS idx_compactions_session ON compactions(session_id);
CREATE INDEX IF NOT EXISTS idx_subagents_session ON subagents(session_id);
CREATE INDEX IF NOT EXISTS idx_harvest_path ON harvest_log(file_path);

-- Vault file index: every markdown file in the Obsidian vault
CREATE TABLE IF NOT EXISTS vault_files (
    id              INTEGER PRIMARY KEY,
    file_path       TEXT NOT NULL UNIQUE,    -- absolute path
    vault_relative  TEXT NOT NULL,           -- path relative to vault root
    domain          TEXT,                    -- inferred from path
    title           TEXT,                    -- first # heading or filename
    frontmatter     TEXT,                    -- raw YAML/field:: frontmatter
    content_text    TEXT,                    -- full file content for FTS
    char_count      INTEGER DEFAULT 0,
    word_count      INTEGER DEFAULT 0,
    file_hash       TEXT,                    -- SHA-256 for change detection
    file_mtime      TEXT,                    -- ISO 8601 last modified
    file_size       INTEGER,
    created_at      TEXT,                    -- file creation time
    harvested_at    TEXT NOT NULL,
    harvest_version INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_vault_files_path ON vault_files(vault_relative);
CREATE INDEX IF NOT EXISTS idx_vault_files_domain ON vault_files(domain);
CREATE INDEX IF NOT EXISTS idx_vault_files_mtime ON vault_files(file_mtime);

-- FTS5 for vault file content
CREATE VIRTUAL TABLE IF NOT EXISTS fts_vault_files USING fts5(
    vault_relative,
    title,
    content_text,
    content='vault_files',
    content_rowid='id',
    tokenize='porter unicode61 remove_diacritics 2'
);

-- FTS sync triggers for vault files
CREATE TRIGGER IF NOT EXISTS fts_vault_files_ai AFTER INSERT ON vault_files
WHEN NEW.content_text IS NOT NULL AND NEW.content_text != ''
BEGIN
    INSERT INTO fts_vault_files(rowid, vault_relative, title, content_text)
        VALUES (NEW.id, NEW.vault_relative, NEW.title, NEW.content_text);
END;

CREATE TRIGGER IF NOT EXISTS fts_vault_files_ad AFTER DELETE ON vault_files
WHEN OLD.content_text IS NOT NULL AND OLD.content_text != ''
BEGIN
    INSERT INTO fts_vault_files(fts_vault_files, rowid, vault_relative, title, content_text)
        VALUES ('delete', OLD.id, OLD.vault_relative, OLD.title, OLD.content_text);
END;

CREATE TRIGGER IF NOT EXISTS fts_vault_files_au AFTER UPDATE ON vault_files
WHEN OLD.content_text IS NOT NULL AND OLD.content_text != ''
BEGIN
    INSERT INTO fts_vault_files(fts_vault_files, rowid, vault_relative, title, content_text)
        VALUES ('delete', OLD.id, OLD.vault_relative, OLD.title, OLD.content_text);
    INSERT INTO fts_vault_files(rowid, vault_relative, title, content_text)
        VALUES (NEW.id, NEW.vault_relative, NEW.title, NEW.content_text);
END;

-- Unified FTS for vault files
CREATE TRIGGER IF NOT EXISTS fts_unified_vault_ai AFTER INSERT ON vault_files
WHEN NEW.content_text IS NOT NULL AND length(NEW.content_text) > 20
BEGIN
    INSERT INTO fts_unified(source_type, session_uuid, domain, timestamp, content_text)
    VALUES ('vault_file', 'vault-' || NEW.id, NEW.domain, NEW.file_mtime, NEW.content_text);
END;

-- FTS5 full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(
    content_text,
    content='messages',
    content_rowid='id',
    tokenize='porter unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_unified USING fts5(
    source_type,
    session_uuid,
    domain,
    timestamp,
    content_text,
    tokenize='porter unicode61 remove_diacritics 2'
);

-- FTS sync triggers
CREATE TRIGGER IF NOT EXISTS fts_messages_ai AFTER INSERT ON messages
WHEN NEW.content_text IS NOT NULL AND NEW.content_text != ''
BEGIN
    INSERT INTO fts_messages(rowid, content_text) VALUES (NEW.id, NEW.content_text);
END;

CREATE TRIGGER IF NOT EXISTS fts_messages_ad AFTER DELETE ON messages
WHEN OLD.content_text IS NOT NULL AND OLD.content_text != ''
BEGIN
    INSERT INTO fts_messages(fts_messages, rowid, content_text)
        VALUES ('delete', OLD.id, OLD.content_text);
END;

CREATE TRIGGER IF NOT EXISTS fts_unified_msg_ai AFTER INSERT ON messages
WHEN NEW.content_text IS NOT NULL AND NEW.content_text != '' AND length(NEW.content_text) > 20
BEGIN
    INSERT INTO fts_unified(source_type, session_uuid, domain, timestamp, content_text)
    SELECT
        CASE NEW.role
            WHEN 'user' THEN 'user_message'
            WHEN 'assistant' THEN 'assistant_message'
            ELSE 'system_message'
        END,
        s.session_uuid,
        s.primary_domain,
        NEW.timestamp,
        NEW.content_text
    FROM sessions s WHERE s.id = NEW.session_id;
END;

-- Views
CREATE VIEW IF NOT EXISTS v_recent_sessions AS
SELECT
    s.id,
    s.session_uuid,
    s.source,
    s.started_at,
    s.ended_at,
    CAST(s.duration_ms / 60000.0 AS INTEGER) AS duration_min,
    s.primary_domain,
    s.domains,
    s.purpose,
    s.primary_model,
    s.message_count,
    s.tool_use_count,
    s.total_input_tokens,
    s.total_output_tokens,
    s.estimated_cost_usd,
    s.subagent_count,
    s.compact_count,
    s.first_prompt,
    s.summary
FROM sessions s
ORDER BY s.started_at DESC;

CREATE VIEW IF NOT EXISTS v_domain_summary AS
SELECT
    COALESCE(s.primary_domain, 'UNCLASSIFIED') AS domain,
    COUNT(*) AS session_count,
    SUM(s.message_count) AS total_messages,
    SUM(s.tool_use_count) AS total_tool_uses,
    SUM(s.total_output_tokens) AS total_output_tokens,
    SUM(s.estimated_cost_usd) AS total_cost_usd,
    SUM(s.duration_ms) / 60000 AS total_minutes
FROM sessions s
GROUP BY s.primary_domain
ORDER BY total_messages DESC;

CREATE VIEW IF NOT EXISTS v_daily_activity AS
SELECT
    DATE(s.started_at) AS day,
    COUNT(*) AS sessions,
    SUM(s.message_count) AS messages,
    SUM(s.tool_use_count) AS tools,
    ROUND(SUM(s.estimated_cost_usd), 2) AS cost_usd,
    ROUND(SUM(s.duration_ms) / 3600000.0, 1) AS hours,
    GROUP_CONCAT(DISTINCT s.primary_domain) AS domains
FROM sessions s
GROUP BY DATE(s.started_at)
ORDER BY day DESC;

CREATE VIEW IF NOT EXISTS v_hot_files AS
SELECT
    fo.vault_relative,
    fo.domain,
    COUNT(DISTINCT fo.session_id) AS sessions_touched,
    SUM(fo.operation_count) AS total_operations,
    SUM(CASE WHEN fo.operation = 'read' THEN fo.operation_count ELSE 0 END) AS reads,
    SUM(CASE WHEN fo.operation = 'write' THEN fo.operation_count ELSE 0 END) AS writes,
    SUM(CASE WHEN fo.operation = 'edit' THEN fo.operation_count ELSE 0 END) AS edits,
    MAX(fo.last_at) AS last_touched
FROM file_operations fo
WHERE fo.vault_relative IS NOT NULL
GROUP BY fo.vault_relative
ORDER BY sessions_touched DESC;

CREATE VIEW IF NOT EXISTS v_tool_stats AS
SELECT
    tu.tool_name,
    COUNT(*) AS invocations,
    COUNT(DISTINCT tu.session_id) AS sessions_used,
    SUM(CASE WHEN tu.is_error = 1 THEN 1 ELSE 0 END) AS errors,
    ROUND(100.0 * SUM(CASE WHEN tu.is_error = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS error_pct
FROM tool_uses tu
GROUP BY tu.tool_name
ORDER BY invocations DESC;
