-- Reinforce realtime table indexes for retention range scans and cleanup.
-- CREATE INDEX CONCURRENTLY cannot run inside a transaction block.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_ticks_quote_time_id
ON public.realtime_price_ticks(quote_time ASC, id ASC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_ticks_holding_id
ON public.realtime_price_ticks(holding_id)
WHERE holding_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_realtime_price_bars_interval_bucket
ON public.realtime_price_bars(interval, bucket_start);
