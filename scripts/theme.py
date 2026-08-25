"""Shared monochrome color tokens for the generated SVG widgets.

Keeping colors in one place so stats.svg, the project cards, and the
activity graph always stay visually consistent across dark/light.
"""
from datetime import datetime, timezone

FONT = 'font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif"'

THEMES = {
    "dark": {
        "bg": "#0d0d0d",
        "border": "#2b2b2b",
        "title": "#ffffff",
        "text": "#b3b3b3",
        "text_dim": "#9a9a9a",
        "text_dimmer": "#6e6e6e",
        "bar_track": "#1f1f1f",
        "bar_fill": "#ffffff",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d8d8d8",
        "title": "#0d0d0d",
        "text": "#4d4d4d",
        "text_dim": "#5c5c5c",
        "text_dimmer": "#8a8a8a",
        "bar_track": "#e9e9e9",
        "bar_fill": "#0d0d0d",
    },
}


def get_theme(name):
    return THEMES[name]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def relative_time(iso_str):
    then = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - then
    days = delta.days
    if days < 1:
        hours = delta.seconds // 3600
        return f"{hours}h ago" if hours else "just now"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"
