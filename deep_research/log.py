"""Structured logging with colored console output and optional file handler."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

_run_id: ContextVar[str] = ContextVar("run_id", default="")
_file_handler: ContextVar[logging.FileHandler | None] = ContextVar("_file_handler", default=None)

RESET = "\033[0m"
GRAY = "\033[90m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
MAGENTA = "\033[35m"

LEVEL_COLORS = {
    logging.DEBUG: GRAY,
    logging.INFO: GREEN,
    logging.WARNING: YELLOW,
    logging.ERROR: RED,
    logging.CRITICAL: RED + BOLD,
}

LEVEL_LABELS = {
    logging.DEBUG: "DBG",
    logging.INFO: "INF",
    logging.WARNING: "WRN",
    logging.ERROR: "ERR",
    logging.CRITICAL: "CRT",
}


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%H:%M:%S")
        rid = _run_id.get()
        lc = LEVEL_COLORS.get(record.levelno, "")
        label = LEVEL_LABELS.get(record.levelno, "???")
        rid_str = f" {MAGENTA}[{rid}]{RESET}" if rid else ""
        return f"{GRAY}{ts}{RESET}{rid_str} {lc}{label}{RESET} {record.getMessage()}"


class FileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%H:%M:%S")
        rid = _run_id.get()
        label = LEVEL_LABELS.get(record.levelno, "???")
        rid_str = f" [{rid}]" if rid else ""
        return f"{ts}{rid_str} {label} {record.getMessage()}"


_console = logging.StreamHandler(sys.stdout)
_console.setFormatter(ColorFormatter())

log = logging.getLogger("deep-research")
log.handlers.clear()
log.addHandler(_console)
log.setLevel(logging.DEBUG)
log.propagate = False

# Quiet noisy libs
for noisy in ("httpx", "httpcore", "openai", "azure", "urllib3", "trafilatura"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def new_run_id() -> str:
    """Generate a short run ID from timestamp."""
    rid = datetime.now(UTC).strftime("%H%M%S")
    _run_id.set(rid)
    return rid


def get_run_id() -> str:
    return _run_id.get()


def attach_file_handler(research_dir: str) -> Path:
    """Attach a file handler that writes to research_dir/run.log."""
    old = _file_handler.get()
    if old:
        log.removeHandler(old)
        old.close()

    log_dir = Path(research_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    path = log_dir / "run.log"
    fh = logging.FileHandler(path, mode="a", encoding="utf-8")
    fh.setFormatter(FileFormatter())
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)
    _file_handler.set(fh)
    log.debug("Log file: %s", path)
    return path


def detach_file_handler() -> None:
    fh = _file_handler.get()
    if fh:
        log.removeHandler(fh)
        fh.close()
        _file_handler.set(None)
