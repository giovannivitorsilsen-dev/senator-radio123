"""Local restriction notices. No credentials or remote polling."""
import sqlite3
from contextlib import closing
from datetime import datetime
from email.utils import parsedate_to_datetime
from time import time


def retry_time(value, now):
    try:
        value = str(value).strip()
        if value.isascii() and value.isdecimal():
            result = now + int(value)
        else:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                return None
            result = date.timestamp()
        datetime.fromtimestamp(result)
        return max(now, result)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def restriction(error, now, fallback=None):
    if isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {"ClientConnectionError", "ConnectTimeout", "ReadTimeout"}:
        return None
    cause = error
    while cause is not None:
        response = getattr(cause, "response", None)
        if response is None:
            response = fallback
        if (getattr(response, "status_code", None) == 429 or
                type(cause).__name__ in {"PleaseWaitFewMinutes", "FeedbackRequired",
                                         "RateLimitError", "ClientThrottledError"}):
            headers = getattr(response, "headers", {})
            return now, retry_time(headers.get("Retry-After"), now)
        cause = cause.__cause__
    return None


class Pauses:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS pauses (account TEXT PRIMARY KEY, started REAL NOT NULL, until REAL)")

    def record(self, user, notice):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR REPLACE INTO pauses VALUES (?,?,?)", (user.strip().casefold(), *notice))

    def get(self, user):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT started, until FROM pauses WHERE account=?", (user.strip().casefold(),)).fetchone()

    def clear_verified(self, user, now):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM pauses WHERE account=? AND (until IS NULL OR until<=?)",
                       (user.strip().casefold(), now))


def describe(notice, now=None):
    now = time() if now is None else now
    started, until = notice
    def stamp(value):
        return datetime.fromtimestamp(value).strftime("%d/%m/%Y %H:%M")
    if until is None:
        return f"In pausa dal {stamp(started)}. Instagram non ha indicato una scadenza."
    if now < until:
        return f"In pausa fino al {stamp(until)} (ora del telefono)."
    return "Attesa indicata terminata. Verifica la funzione in Instagram."
