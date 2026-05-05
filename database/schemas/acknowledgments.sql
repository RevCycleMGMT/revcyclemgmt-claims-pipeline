CREATE TABLE IF NOT EXISTS acknowledgments (
  claim_id TEXT,
  ack_type TEXT,
  status TEXT,
  received_at TIMESTAMP,
  control_number TEXT,
  _hash TEXT
);
