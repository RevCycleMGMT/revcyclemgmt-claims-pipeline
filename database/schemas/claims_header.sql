-- Example schema (adjust for your warehouse)
CREATE TABLE IF NOT EXISTS claims_header (
  claim_id TEXT PRIMARY KEY,
  member_id TEXT,
  payer TEXT,
  claim_type TEXT,
  dos_from DATE,
  dos_to DATE,
  place_of_service TEXT,
  billed_amt NUMERIC,
  rendering_provider_npi TEXT,
  _hash TEXT
);
