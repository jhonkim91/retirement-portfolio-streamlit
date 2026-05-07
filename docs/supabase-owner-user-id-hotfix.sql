-- Supabase 운영 RLS 핫픽스
-- 목적:
-- 1. accounts 테이블에 owner_user_id를 추가해 auth.uid()와 직접 매핑한다.
-- 2. 기존 name prefix 기반 정책을 owner_user_id 기반 정책으로 교체한다.
-- 3. 첫 계좌 생성 / 데모 데이터 생성 시 발생하는 INSERT RLS 403을 해소한다.

BEGIN;

ALTER TABLE public.accounts
    ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

UPDATE public.accounts
SET owner_user_id = NULLIF(split_part(name, '::', 1), '')::uuid
WHERE owner_user_id IS NULL
  AND split_part(name, '::', 1) ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

ALTER TABLE public.accounts
    ALTER COLUMN owner_user_id SET DEFAULT auth.uid();

CREATE INDEX IF NOT EXISTS idx_accounts_owner_user_id ON public.accounts(owner_user_id);

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

COMMIT;
