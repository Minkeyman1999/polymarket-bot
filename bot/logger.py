"""
logger.py — Simple logging
───────────────────────────
Writes timestamped log messages to:
  - Console (visible in GitHub Actions run logs)
  - logs/bot.log (persists in repo if you commit it)
"""

import os
from datetime import datetime, timezone


LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "bot.log")


def log(message):
    """
    Log a message with a UTC timestamp.
    Prints to console AND appends to logs/bot.log
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {message}"

    # Always print to console (shows in GitHub Actions)
    print(line)

    # Also write to file
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass  # Don't crash the bot if logging fails
