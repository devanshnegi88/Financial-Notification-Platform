import hashlib
import json
from typing import Any, Dict
from uuid import UUID


def generate_idempotency_key(
    user_id: UUID,
    event_type: str,
    channel: str,
    event_data: Dict[str, Any],
) -> str:
    """Generate a deterministic idempotency key from event parameters."""
    payload = {
        "user_id": str(user_id),
        "event_type": event_type,
        "channel": channel,
        # Only include stable, identifying fields from event_data
        "ref": event_data.get("reference_id") or event_data.get("transaction_id") or "",
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:64]
