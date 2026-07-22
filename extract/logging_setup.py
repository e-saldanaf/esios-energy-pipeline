"""Structured logging for the pipeline.

DIDACTIC NOTE — Dual formatter pattern:
    JSON logs are for machines: log aggregators (CloudWatch, Kibana, Grafana
    Loki) parse fields like `level` or `indicator_id` only if logs are
    structured. But JSON is unreadable in a local terminal.

    Solution: two formatters, one env var to switch.
    - LOG_FORMAT=json  → JSON (default in CI: GitHub Actions sets it)
    - LOG_FORMAT=text  → coloured human-readable (default in local .env)

    The code that emits log calls never changes — only the formatter does.
    Same principle as dbt's target: prod vs dev, same models, different
    warehouse. Separating *what* to log from *how* to format it is the
    logging equivalent of Clean Architecture.

ANSI colour codes (work in VS Code integrated terminal and most Unix
terminals; Windows cmd.exe doesn't support them, but VS Code does):
"""

import json
import logging
import os
from datetime import datetime, timezone

# ── ANSI colours ──────────────────────────────────────────────────────────────
_RESET  = "\033[0m"
_GREY   = "\033[38;5;240m"
_CYAN   = "\033[36m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
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

        # Inline context fields (from extra={"ctx": {...}})
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
    """Pick formatter based on settings.log_format.

    Centralised in Settings like every other config value — no direct
    os.getenv() calls outside of config.py. Consistent with how the rest
    of the project accesses configuration.
    """
    from extract.config import settings  # local import to avoid circular
    return JsonFormatter() if settings.log_format.lower() == "json" else TextFormatter()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_make_formatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger