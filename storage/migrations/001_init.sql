-- 001_init.sql：商品、議價會話、執行日誌三表

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT CHECK(status IN ('DRAFT', 'PUBLISHED', 'SOLD', 'DELISTED')),
    suggested_price INTEGER NOT NULL,
    floor_price INTEGER NOT NULL,
    category TEXT,
    description TEXT,
    images_json TEXT,
    carousell_item_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES products(id),
    buyer_username TEXT NOT NULL,
    buyer_message_id TEXT,
    negotiation_round INTEGER DEFAULT 0,
    current_state TEXT,
    last_buyer_offer INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    task_type TEXT NOT NULL,
    product_id TEXT,
    session_id TEXT,
    status TEXT CHECK(status IN ('SUCCESS', 'FAILURE', 'BLOCKED')),
    screenshot_path TEXT,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_execution_logs_timestamp ON execution_logs(timestamp);
