import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "bot.log")

def log(message):
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {message}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
