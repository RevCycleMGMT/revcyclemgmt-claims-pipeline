# Security Notes

- Secrets via `.env` or a secret manager, never in code.
- Rotate SFTP/AS2 keys periodically.
- Validate envelopes (ISA/GS/ST) and checksum files on arrival.
- ACK SLAs: alert if 999/277CA not received within configured windows.
- Hash and lineage: compute deterministic hashes per claim, line, remit, payment, and acknowledgment record.
- Do not commit PHI, production claims, real remittance files, payer credentials, clearinghouse credentials, screenshots containing identifiers, or support exports from real systems.
- Scrub raw X12 values before logging.
- Treat payer companion guides, clearinghouse connection details, and production routing rules as restricted operational material.
