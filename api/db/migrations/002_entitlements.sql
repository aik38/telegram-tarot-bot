PRAGMA foreign_keys = ON;

ALTER TABLE plans ADD COLUMN credit_quota INTEGER NOT NULL DEFAULT 0;
ALTER TABLE plans ADD COLUMN period_days INTEGER NOT NULL DEFAULT 30;

ALTER TABLE entitlements ADD COLUMN credits_used INTEGER NOT NULL DEFAULT 0;
ALTER TABLE entitlements ADD COLUMN period_end TEXT;

ALTER TABLE identities ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP);

ALTER TABLE usage_events ADD COLUMN request_id TEXT;
ALTER TABLE usage_events ADD COLUMN feature TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_request_id ON usage_events (request_id);

INSERT OR IGNORE INTO plans (plan_code, name, credit_quota, period_days)
VALUES ('free', 'Free', 3, 30);
