"""Shared monochrome color tokens for the generated SVG widgets.

Keeping colors in one place so stats.svg, the project cards, and the
activity graph always stay visually consistent across dark/light.
"""

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
