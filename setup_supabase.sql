-- Supabase 초기 테이블 설정
-- 방법: Supabase 대시보드 > SQL Editor > 이 스크립트 모두 복사 & 실행

-- accounts 테이블
CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'retirement',
    cash_balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- holdings 테이블
CREATE TABLE IF NOT EXISTS holdings (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    product_name TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'risk',
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    current_price DOUBLE PRECISION NOT NULL DEFAULT 0,
    price_updated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, symbol),
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- trade_logs 테이블
CREATE TABLE IF NOT EXISTS trade_logs (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL,
    symbol TEXT,
    product_name TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'risk',
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    price DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    trade_date TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- RLS (Row Level Security) 비활성화 (개인 앱이므로)
ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;
ALTER TABLE holdings DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_logs DISABLE ROW LEVEL SECURITY;
