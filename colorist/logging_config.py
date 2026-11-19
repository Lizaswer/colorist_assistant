from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "colorist.md"


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setFormatter(
        logging.Formatter(
            "- **%(levelname)s** `%(name)s` — %(message)s  \n  _%(asctime)s_",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    fh.setLevel(level)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.WARNING)
    root.addHandler(sh)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
