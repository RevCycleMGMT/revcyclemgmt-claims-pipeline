CREATE TABLE IF NOT EXISTS claims_line (
  claim_id TEXT,
  line_no INT,
  hcpcs_cpt TEXT,
  rev_code TEXT,
  units NUMERIC,
  billed NUMERIC,
  allowed NUMERIC,
  paid NUMERIC,
  patient_resp NUMERIC,
  _hash TEXT
);