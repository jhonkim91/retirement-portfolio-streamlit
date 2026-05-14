-- Add company-principal daily valuation snapshots.
-- Run on staging first, then apply to production Supabase SQL Editor.

BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_daily_valuation_snapshot_account_date
ON public.daily_valuation_snapshot(account_id, valuation_date);

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.daily_valuation_snapshot
TO authenticated, service_role;

GRANT USAGE, SELECT
ON SEQUENCE public.daily_valuation_snapshot_id_seq
TO authenticated, service_role;

ALTER TABLE public.daily_valuation_snapshot ENABLE ROW LEVEL SECURITY;

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

COMMIT;
