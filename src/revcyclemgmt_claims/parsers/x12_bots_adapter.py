# Stub adapter for Bots EDI translator.
# Offers the same function signature as the pyx12 adapter.

from typing import Dict, List
from revcyclemgmt_claims.parsers.x12_pyx12_adapter import parse_x12_to_dicts as _parse_demo_payload

def parse_x12_to_dicts(x12_text: str) -> Dict[str, List[dict]]:
    return _parse_demo_payload(x12_text)
