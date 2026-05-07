-- Supabase setup for user-scoped retirement portfolios.
-- The app stores account names as: <auth.uid()>::<visible_account_name>
-- Example: 550e8400-e29b-41d4-a716-446655440000::My IRA

CREATE TABLE IF NOT EXISTS public.accounts (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'retirement',
    cash_balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    price_updated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
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
    trade_date TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_name ON public.accounts(name);
CREATE INDEX IF NOT EXISTS idx_holdings_account_id ON public.holdings(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_logs_account_id ON public.trade_logs(account_id);

GRANT USAGE ON SCHEMA public TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.accounts TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.holdings TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.trade_logs TO authenticated, service_role;

GRANT USAGE, SELECT ON SEQUENCE public.accounts_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.holdings_id_seq TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.trade_logs_id_seq TO authenticated, service_role;

ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS accounts_select_own ON public.accounts;
DROP POLICY IF EXISTS accounts_insert_own ON public.accounts;
DROP POLICY IF EXISTS accounts_update_own ON public.accounts;
DROP POLICY IF EXISTS accounts_delete_own ON public.accounts;

CREATE POLICY accounts_select_own
ON public.accounts
FOR SELECT
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND split_part(name, '::', 1) = auth.uid()::text
);

CREATE POLICY accounts_insert_own
ON public.accounts
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() IS NOT NULL
    AND split_part(name, '::', 1) = auth.uid()::text
);

CREATE POLICY accounts_update_own
ON public.accounts
FOR UPDATE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND split_part(name, '::', 1) = auth.uid()::text
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND split_part(name, '::', 1) = auth.uid()::text
);

CREATE POLICY accounts_delete_own
ON public.accounts
FOR DELETE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND split_part(name, '::', 1) = auth.uid()::text
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
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY holdings_insert_own
ON public.holdings
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY holdings_update_own
ON public.holdings
FOR UPDATE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY holdings_delete_own
ON public.holdings
FOR DELETE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = holdings.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
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
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY trade_logs_insert_own
ON public.trade_logs
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY trade_logs_update_own
ON public.trade_logs
FOR UPDATE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
)
WITH CHECK (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

CREATE POLICY trade_logs_delete_own
ON public.trade_logs
FOR DELETE
TO authenticated
USING (
    auth.uid() IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM public.accounts
        WHERE accounts.id = trade_logs.account_id
          AND split_part(accounts.name, '::', 1) = auth.uid()::text
    )
);

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated, service_role;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO authenticated, service_role;
