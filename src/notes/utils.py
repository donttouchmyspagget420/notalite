import re
import unicodedata
from datetime import datetime, timezone


def time_ago(value):
    if not value:
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    seconds = max(0, int((now - value).total_seconds()))

    if seconds < 60:
        return "hace instantes"
    if seconds < 3600:
        minutes = seconds // 60
        return f"hace {minutes} min"
    if seconds < 86400:
        hours = seconds // 3600
        return f"hace {hours} h"
    if seconds < 172800:
        return "ayer"

    days = seconds // 86400
    return f"hace {days} d"


def slugify(value, fallback="nota"):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or fallback


def note_title_from_markdown(filename, content):
    for line in (content or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title[:255]

    title = (filename or "").rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()
    return (title or "Nota importada")[:255]
