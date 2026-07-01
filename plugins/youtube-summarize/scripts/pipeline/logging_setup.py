import logging
import sys
from logging.handlers import RotatingFileHandler

from pipeline.paths import logs_dir

_configured = False


def setup_logging(level=logging.INFO) -> logging.Logger:
    global _configured
    logger = logging.getLogger("youtube_to_ppt")
    if _configured:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = RotatingFileHandler(logs_dir() / "server.log", maxBytes=1_000_000,
                             backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)   # stderr 전용 — stdout 금지
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    _configured = True
    return logger
