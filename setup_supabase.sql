
-- Supabase setup for user-scoped retirement portfolios.
-- The app stores account names as: <auth.uid()>::<visible_account_name>
-- Example: 550e8400-e29b-41d4-a716-446655440000::My IRA

CREATE TABLE IF NOT EXISTS public.accounts (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    account_type TEXT NOT NULL DEFAULT 'retirement',
    cash_balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS public.holdings (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    product_name TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'risk',
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    current_price DOUBLE PRECISION NOT NULL DEFAULT 0,
    price_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(account_id, symbol)
);

CREATE TABLE IF NOT EXISTS public.trade_logs (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    symbol TEXT,
    product_name TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'risk',
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    price DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    cash_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    event_group_id TEXT,
    counterparty_account_id BIGINT REFERENCES public.accounts(id) ON DELETE SET NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trade_date DATE NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS public.daily_interest (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    interest_amount DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(account_id, date)
);

CREATE TABLE IF NOT EXISTS public.daily_account_snapshot (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    cash_balance DOUBLE PRECISION NOT NULL,
    market_value DOUBLE PRECISION NOT NULL,
    total_value DOUBLE PRECISION NOT NULL,
    total_cost DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS public.daily_valuation_snapshot (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    valuation_date DATE NOT NULL,
    company_principal DOUBLE PRECISION NOT NULL DEFAULT 0,
    invested_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    implied_cash DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_cash_balance DOUBLE PRECISION,
    cash_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    cash_source TEXT NOT NULL DEFAULT 'implied',
    holdings_market_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    valuation_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    profit_loss DOUBLE PRECISION NOT NULL DEFAULT 0,
    profit_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    over_invested_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    missing_price_symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_hash TEXT NOT NULL DEFAULT '',
    calculation_reason TEXT NOT NULL DEFAULT 'auto',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(account_id, valuation_date),
    CHECK (cash_source IN ('implied', 'actual'))
);

CREATE TABLE IF NOT EXISTS public.realtime_price_ticks (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    holding_id BIGINT REFERENCES public.holdings(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    previous_close DOUBLE PRECISION,
    day_change_rate DOUBLE PRECISION,
    currency TEXT NOT NULL DEFAULT 'KRW',
    quote_time TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'KIS WebSocket',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.realtime_price_bars (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    bucket_start TIMESTAMPTZ NOT NULL,
    open_price DOUBLE PRECISION NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    low_price DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    previous_close DOUBLE PRECISION,
    day_change_rate DOUBLE PRECISION,
    tick_count INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'KRW',
    first_quote_at TIMESTAMPTZ NOT NULL,
    last_quote_at TIMESTAMPTZ NOT NULL,
    aggregated_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'tick-retention',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(account_id, symbol, interval, bucket_start),
    CHECK (interval IN ('1m', '5m', '1d'))
);

CREATE TABLE IF NOT EXISTS public.realtime_worker_status (
    account_id BIGINT PRIMARY KEY REFERENCES public.accounts(id) ON DELETE CASCADE,
    worker_name TEXT NOT NULL,
    connection_state TEXT NOT NULL,
    last_seen_at TIMESTAMPTZ,
    last_quote_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE public.accounts
    ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE public.trade_logs
    ADD COLUMN IF NOT EXISTS cash_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS event_group_id TEXT,
    ADD COLUMN IF NOT EXISTS counterparty_account_id BIGINT REFERENCES public.accounts(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE public.accounts
SET owner_user_id = NULLIF(split_part(name, '::', 1), '')::uuid
WHERE owner_user_id IS NULL
  AND split_part(name, '::', 1) ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

ALTER TABLE public.accounts
    ALTER COLUMN owner_user_id SET DEFAULT auth.uid();

CREATE INDEX IF NOT EXISTS idx_accounts_name ON public.accounts(name);
CREATE INDEX IF NOT EXISTS idx_accounts_owner_user_id ON public.accounts(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_account_id ON public.holdings(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_logs_account_id ON public.trade_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_logs_event_group_id ON public.trade_logs(event_group_id);
CREATE INDEX IF NOT EXISTS idx_daily_interest_account_date ON public.daily_interest(account_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_account_snapshot_account_date ON public.daily_account_snapshot(account_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_daily_valuation_snapshot_account_date ON public.daily_valuation_snapshot(account_id, valuation_date);
CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_account_quote_time ON public.realtime_price_ticks(account_id, quote_time DESC);
CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_symbol_quote_time ON public.realtime_price_ticks(symbol, quote_time DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_ticks_quote_time_id ON public.realtime_price_ticks(quote_time ASC, id ASC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_ticks_holding_id ON public.realtime_price_ticks(holding_id) WHERE holding_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_realtime_price_bars_account_interval_bucket ON public.realtime_price_bars(account_id, interval, bucket_start DESC);
CREATE INDEX IF NOT EXISTS idx_realtime_price_bars_symbol_interval_bucket ON public.realtime_price_bars(symbol, interval, bucket_start DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_bars_interval_bucket ON public.realtime_price_bars(interval, bucket_start);

UPDATE public.trade_logs
SET trade_type = 'personal_deposit'
WHERE trade_type = 'deposit';

UPDATE public.trade_logs
SET metadata_json = '{}'::jsonb
WHERE metadata_json IS NULL;

UPDATE public.trade_logs
SET asset_type = 'cash',
    quantity = 0,
    price = 0,
    product_name = CASE
        WHEN trade_type = 'personal_deposit' AND COALESCE(product_name, '') IN ('', '현금 입금', '현금 흐름') THEN '개인 입금'
        WHEN trade_type = 'withdraw' AND COALESCE(product_name, '') IN ('', '현금 출금', '현금 흐름') THEN '일반 출금'
        WHEN trade_type = 'interest' AND COALESCE(product_name, '') = '' THEN '일별 이자'
        WHEN trade_type = 'transfer_out' AND COALESCE(product_name, '') = '' THEN '계좌 이체 출금'
        WHEN trade_type = 'transfer_in' AND COALESCE(product_name, '') = '' THEN '계좌 이체 입금'
        WHEN trade_type = 'cash_adjustment' AND COALESCE(product_name, '') = '' THEN '현금 조정'
        WHEN trade_type = 'employer_deposit' AND COALESCE(product_name, '') = '' THEN '회사 납입금'
        ELSE product_name
    END
WHERE trade_type IN ('personal_deposit', 'employer_deposit', 'withdraw', 'interest', 'transfer_out', 'transfer_in', 'cash_adjustment');

UPDATE public.trade_logs
SET cash_delta = CASE
    WHEN trade_type = 'buy' THEN -ABS(total_amount)
    WHEN trade_type = 'sell' THEN ABS(total_amount)
    WHEN trade_type IN ('personal_deposit', 'employer_deposit', 'interest', 'transfer_in') THEN ABS(total_amount)
    WHEN trade_type IN ('withdraw', 'transfer_out') THEN -ABS(total_amount)
    ELSE COALESCE(cash_delta, 0)
END
WHERE trade_type IN ('buy', 'sell', 'personal_deposit', 'employer_deposit', 'withdraw', 'interest', 'transfer_out', 'transfer_in');

GRANT USAGE ON SCHEMA public TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.accounts TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.holdings TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.trade_logs TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.daily_interest TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.daily_account_snapshot TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.daily_valuation_snapshot TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.realtime_price_ticks TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.realtime_price_bars TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.realtime_worker_status TO authenticated, service_role;

GRANT USAGE, SELECT ON SEQUENCE public.accounts_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.holdings_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.trade_logs_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.daily_interest_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.daily_account_snapshot_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.daily_valuation_snapshot_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.realtime_price_ticks_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.realtime_price_bars_id_seq TO authenticated, service_role;

ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_interest ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_account_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_valuation_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.realtime_price_ticks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.realtime_price_bars ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.realtime_worker_status ENABLE ROW LEVEL SECURITY;

-- SQL Editor에서 정책 일부만 재실행할 때 현재 정책 상태를 먼저 확인한다.
-- SELECT policyname, tablename
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;

DROP POLICY IF EXISTS accounts_select_own ON public.accounts;
DROP POLICY IF EXISTS accounts_insert_own ON public.accounts;
DROP POLICY IF EXISTS accounts_update_own ON public.accounts;
DROP POLICY IF EXISTS accounts_delete_own ON public.accounts;

CREATE POLICY accounts_select_own
ON public.accounts
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND owner_user_id = (select auth.uid())
);

CREATE POLICY accounts_insert_own
ON public.accounts
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND owner_user_id = (select auth.uid())
);

CREATE POLICY accounts_update_own
ON public.accounts
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND owner_user_id = (select auth.uid())
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND owner_user_id = (select auth.uid())
);

CREATE POLICY accounts_delete_own
ON public.accounts
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND owner_user_id = (select auth.uid())
);

DROP POLICY IF EXISTS holdings_select_own ON public.holdings;
DROP POLICY IF EXISTS holdings_insert_own ON public.holdings;
DROP POLICY IF EXISTS holdings_update_own ON public.holdings;
DROP POLICY IF EXISTS holdings_delete_own ON public.holdings;

CREATE POLICY holdings_select_own
ON public.holdings
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY holdings_insert_own
ON public.holdings
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

-- SQL Editor에서 이 블록만 다시 실행해도 duplicate policy 오류가 나지 않도록 한 번 더 정리한다.
DROP POLICY IF EXISTS holdings_update_own ON public.holdings;

CREATE POLICY holdings_update_own
ON public.holdings
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY holdings_delete_own
ON public.holdings
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS trade_logs_select_own ON public.trade_logs;
DROP POLICY IF EXISTS trade_logs_insert_own ON public.trade_logs;
DROP POLICY IF EXISTS trade_logs_update_own ON public.trade_logs;
DROP POLICY IF EXISTS trade_logs_delete_own ON public.trade_logs;

CREATE POLICY trade_logs_select_own
ON public.trade_logs
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY trade_logs_insert_own
ON public.trade_logs
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY trade_logs_update_own
ON public.trade_logs
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY trade_logs_delete_own
ON public.trade_logs
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS daily_interest_select_own ON public.daily_interest;
DROP POLICY IF EXISTS daily_interest_insert_own ON public.daily_interest;
DROP POLICY IF EXISTS daily_interest_update_own ON public.daily_interest;
DROP POLICY IF EXISTS daily_interest_delete_own ON public.daily_interest;

CREATE POLICY daily_interest_select_own
ON public.daily_interest
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_interest.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_interest_insert_own
ON public.daily_interest
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_interest.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

-- SQL Editor에서 이 블록만 다시 실행해도 duplicate policy 오류가 나지 않도록 한 번 더 정리한다.
DROP POLICY IF EXISTS daily_interest_update_own ON public.daily_interest;

CREATE POLICY daily_interest_update_own
ON public.daily_interest
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_interest.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_interest.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_interest_delete_own
ON public.daily_interest
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_interest.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS daily_account_snapshot_select_own ON public.daily_account_snapshot;
DROP POLICY IF EXISTS daily_account_snapshot_insert_own ON public.daily_account_snapshot;
DROP POLICY IF EXISTS daily_account_snapshot_update_own ON public.daily_account_snapshot;
DROP POLICY IF EXISTS daily_account_snapshot_delete_own ON public.daily_account_snapshot;

CREATE POLICY daily_account_snapshot_select_own
ON public.daily_account_snapshot
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_account_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_account_snapshot_insert_own
ON public.daily_account_snapshot
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_account_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_account_snapshot_update_own
ON public.daily_account_snapshot
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_account_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_account_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_account_snapshot_delete_own
ON public.daily_account_snapshot
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_account_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS daily_valuation_snapshot_select_own ON public.daily_valuation_snapshot;
DROP POLICY IF EXISTS daily_valuation_snapshot_insert_own ON public.daily_valuation_snapshot;
DROP POLICY IF EXISTS daily_valuation_snapshot_update_own ON public.daily_valuation_snapshot;
DROP POLICY IF EXISTS daily_valuation_snapshot_delete_own ON public.daily_valuation_snapshot;

CREATE POLICY daily_valuation_snapshot_select_own
ON public.daily_valuation_snapshot
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_valuation_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_valuation_snapshot_insert_own
ON public.daily_valuation_snapshot
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_valuation_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_valuation_snapshot_update_own
ON public.daily_valuation_snapshot
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_valuation_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_valuation_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY daily_valuation_snapshot_delete_own
ON public.daily_valuation_snapshot
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = daily_valuation_snapshot.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS realtime_price_ticks_select_own ON public.realtime_price_ticks;
DROP POLICY IF EXISTS realtime_price_ticks_insert_own ON public.realtime_price_ticks;
DROP POLICY IF EXISTS realtime_price_ticks_update_own ON public.realtime_price_ticks;
DROP POLICY IF EXISTS realtime_price_ticks_delete_own ON public.realtime_price_ticks;

CREATE POLICY realtime_price_ticks_select_own
ON public.realtime_price_ticks
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_ticks.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_ticks_insert_own
ON public.realtime_price_ticks
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_ticks.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_ticks_update_own
ON public.realtime_price_ticks
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_ticks.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_ticks.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_ticks_delete_own
ON public.realtime_price_ticks
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_ticks.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS realtime_price_bars_select_own ON public.realtime_price_bars;
DROP POLICY IF EXISTS realtime_price_bars_insert_own ON public.realtime_price_bars;
DROP POLICY IF EXISTS realtime_price_bars_update_own ON public.realtime_price_bars;
DROP POLICY IF EXISTS realtime_price_bars_delete_own ON public.realtime_price_bars;

CREATE POLICY realtime_price_bars_select_own
ON public.realtime_price_bars
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_bars.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_bars_insert_own
ON public.realtime_price_bars
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_bars.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_bars_update_own
ON public.realtime_price_bars
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_bars.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_bars.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_price_bars_delete_own
ON public.realtime_price_bars
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_price_bars.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

DROP POLICY IF EXISTS realtime_worker_status_select_own ON public.realtime_worker_status;
DROP POLICY IF EXISTS realtime_worker_status_insert_own ON public.realtime_worker_status;
DROP POLICY IF EXISTS realtime_worker_status_update_own ON public.realtime_worker_status;
DROP POLICY IF EXISTS realtime_worker_status_delete_own ON public.realtime_worker_status;

CREATE POLICY realtime_worker_status_select_own
ON public.realtime_worker_status
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_worker_status.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_worker_status_insert_own
ON public.realtime_worker_status
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_worker_status.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_worker_status_update_own
ON public.realtime_worker_status
FOR UPDATE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_worker_status.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
)
WITH CHECK (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_worker_status.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

CREATE POLICY realtime_worker_status_delete_own
ON public.realtime_worker_status
FOR DELETE
TO authenticated
USING (
    (select auth.uid()) IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = realtime_worker_status.account_id
          AND accounts.owner_user_id = (select auth.uid())
    )
);

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated, service_role;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO authenticated, service_role;
