
import logging
import json
from datetime import datetime, timezone


logger = logging.getLogger("inventory_orchestrator")


def log_event(event: str, **details):
    """Emit a structured JSON log entry."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }

    logger.info(json.dumps(payload, default=str))
