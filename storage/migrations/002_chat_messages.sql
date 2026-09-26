-- 002_chat_messages.sql：議價對話緩衝（非向量記憶，每會話保留最近 20 則）

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    role TEXT NOT NULL CHECK(role IN ('buyer', 'agent', 'system')),
    text TEXT NOT NULL,
    amount_parsed INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);
