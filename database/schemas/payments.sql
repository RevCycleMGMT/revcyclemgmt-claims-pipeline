CREATE TABLE IF NOT EXISTS payments (
  claim_id TEXT,
  check_eft_no TEXT,
  payer TEXT,
  amount NUMERIC,
  post_date DATE,
  trace_no TEXT,
  _hash TEXT
);