"""Structured logging for the pipeline.

DIDACTIC NOTE — Dual formatter pattern:
    JSON logs are for machines: log aggregators (CloudWatch, Kibana, Grafana
    Loki) parse fields like `level` or `indicator_id` only if logs are
    structured. But JSON is unreadable in a local terminal.

    Solution: two formatters, one env var to switch.
    - LOG_FORMAT=json  → JSON (default in CI: set at job level in Actions)
    - LOG_FORMAT=text  → coloured human-readable (default locally)

    DIDACTIC NOTE — Why os.getenv here and not settings:
    logging_setup is imported at module load time by every other module.
    Importing settings here would create a circular dependency AND would
    require credentials to be present even when running pure unit tests.
    LOG_FORMAT is infrastructure config (how to display), not business
    config (what to do) — os.getenv is the correct tool for this layer.
"""

import json
import logging
import os
from datetime import datetime, timezone

# ── ANSI colours ──────────────────────────────────────────────────────────────
_RESET    = "\033[0m"
_GREY     = "\033[38;5;240m"
_CYAN     = "\033[36m"
_YELLOW   = "\033[33m"
_RED      = "\033[31m"
_BOLD_RED = "\033[1;31m"

_LEVEL_COLOURS = {
    "DEBUG":    _GREY,
    "INFO":     _CYAN,
    "WARNING":  _YELLOW,
    "ERROR":    _RED,
    "CRITICAL": _BOLD_RED,
}

# ── Formatters ────────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Machine-readable JSON — use in CI / production."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "ctx"):
            payload.update(record.ctx)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable coloured output — use in local development."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, _RESET)
        ts     = datetime.now(timezone.utc).strftime("%H:%M:%S")
        level  = f"{colour}{record.levelname:<8}{_RESET}"
        logger = f"{_GREY}{record.name}{_RESET}"
        msg    = record.getMessage()

        ctx = ""
        if hasattr(record, "ctx"):
            parts = [f"{k}={v}" for k, v in record.ctx.items()]
            ctx = f"  {_GREY}({', '.join(parts)}){_RESET}"

        line = f"{_GREY}{ts}{_RESET}  {level}  {logger}  {msg}{ctx}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


# ── Factory ───────────────────────────────────────────────────────────────────

def _make_formatter() -> logging.Formatter:
    """Pick formatter based on LOG_FORMAT env var.

    Reads os.getenv directly — intentionally does NOT use settings.
    See module docstring for the reasoning.

    Defaults to 'text' so local runs are readable without any config.
    CI sets LOG_FORMAT=json at job level in the workflow.
    """
    fmt = os.getenv("LOG_FORMAT", "text").lower()
    return JsonFormatter() if fmt == "json" else TextFormatter()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_make_formatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger