"""Structured JSON logging for the pipeline.

DIDACTIC NOTE — Why JSON logs in a toy project:
    Plain-text logs are for humans reading a terminal. Structured logs are
    for MACHINES: log aggregators (CloudWatch, Kibana, Grafana Loki) can
    filter/alert on fields like `level` or `indicator_id` only if logs are
    parseable. GitHub Actions output is plain text today, but the habit —
    and the code — transfers 1:1 to enterprise environments.

    Rule of thumb: log EVENTS with CONTEXT, not prose.
        Bad:  "Something went wrong loading data"
        Good: {"event": "merge_completed", "indicator_id": 600, "rows": 24}
"""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Allow structured extras: logger.info("merge", extra={"ctx": {...}})
        if hasattr(record, "ctx"):
            payload.update(record.ctx)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid duplicate handlers on re-import
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
