import os
import glob
from datetime import datetime, timezone

LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
MAX_LOG_SIZE = 1_000_000  # 1MB
MAX_BACKUPS  = 5


def _rotate():
    """Rotate log file if it exceeds MAX_LOG_SIZE."""
    try:
        if not os.path.exists(LOG_FILE):
            return
        if os.path.getsize(LOG_FILE) < MAX_LOG_SIZE:
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup = os.path.join(LOG_DIR, f"bot_{ts}.log")
        os.rename(LOG_FILE, backup)
        # Remove old backups beyond limit
        backups = sorted(glob.glob(os.path.join(LOG_DIR, "bot_*.log")))
        for old in backups[:-MAX_BACKUPS]:
            os.remove(old)
    except Exception:
        pass


def log(message: str) -> None:
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {message}"
    print(line)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        _rotate()
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
