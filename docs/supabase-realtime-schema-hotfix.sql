-- Focused production hotfix for KIS realtime worker storage on Supabase.
-- Apply this in Supabase SQL Editor when the project already has accounts/holdings
-- but REST requests for public.realtime_worker_status or public.realtime_price_ticks
-- still return PGRST205.

CREATE TABLE IF NOT EXISTS public.realtime_price_ticks (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    holding_id BIGINT REFERENCES public.holdings(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    previous_close DOUBLE PRECISION,
    day_change_rate DOUBLE PRECISION,
    currency TEXT NOT NULL DEFAULT 'KRW',
    quote_time TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'KIS WebSocket',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.realtime_worker_status (
    account_id BIGINT PRIMARY KEY REFERENCES public.accounts(id) ON DELETE CASCADE,
    worker_name TEXT NOT NULL,
    connection_state TEXT NOT NULL,
    last_seen_at TEXT,
    last_quote_at TEXT,
    updated_at TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_account_quote_time
    ON public.realtime_price_ticks(account_id, quote_time DESC);

CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_symbol_quote_time
    ON public.realtime_price_ticks(symbol, quote_time DESC);

GRANT USAGE ON SCHEMA public TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.realtime_price_ticks TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.realtime_worker_status TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.realtime_price_ticks_id_seq TO authenticated, service_role;

ALTER TABLE public.realtime_price_ticks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.realtime_worker_status ENABLE ROW LEVEL SECURITY;

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

NOTIFY pgrst, 'reload schema';
