-- Normalize temporal columns away from TEXT for Supabase/Postgres.
-- Run on staging first. If any legacy value cannot be cast, PostgreSQL will abort
-- the transaction and expose the row family that needs cleanup before production.

BEGIN;

ALTER TABLE public.accounts
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz,
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::timestamptz;

ALTER TABLE public.holdings
  ALTER COLUMN price_updated_at TYPE TIMESTAMPTZ USING nullif(price_updated_at, '')::timestamptz,
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz,
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::timestamptz;

ALTER TABLE public.trade_logs
  ALTER COLUMN trade_date TYPE DATE USING left(trade_date, 10)::date,
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz;

ALTER TABLE public.daily_interest
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz;

ALTER TABLE public.daily_account_snapshot
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz,
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::timestamptz;

ALTER TABLE public.realtime_price_ticks
  ALTER COLUMN quote_time TYPE TIMESTAMPTZ USING quote_time::timestamptz,
  ALTER COLUMN ingested_at TYPE TIMESTAMPTZ USING ingested_at::timestamptz;

ALTER TABLE public.realtime_price_bars
  ALTER COLUMN bucket_start TYPE TIMESTAMPTZ USING bucket_start::timestamptz,
  ALTER COLUMN first_quote_at TYPE TIMESTAMPTZ USING first_quote_at::timestamptz,
  ALTER COLUMN last_quote_at TYPE TIMESTAMPTZ USING last_quote_at::timestamptz,
  ALTER COLUMN aggregated_at TYPE TIMESTAMPTZ USING aggregated_at::timestamptz;

ALTER TABLE public.realtime_worker_status
  ALTER COLUMN last_seen_at TYPE TIMESTAMPTZ USING nullif(last_seen_at, '')::timestamptz,
  ALTER COLUMN last_quote_at TYPE TIMESTAMPTZ USING nullif(last_quote_at, '')::timestamptz,
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::timestamptz;

COMMIT;
