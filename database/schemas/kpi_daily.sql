CREATE TABLE IF NOT EXISTS kpi_daily (
  as_of_date DATE DEFAULT CURRENT_DATE,
  fpccr NUMERIC,
  denial_rate NUMERIC,
  dnar NUMERIC, -- days in AR (average)
  payer_lag NUMERIC
);