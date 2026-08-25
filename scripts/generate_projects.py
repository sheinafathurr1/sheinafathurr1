#!/usr/bin/env python3
"""Generate self-hosted, monochrome pinned-project cards as plain SVG.

Same rationale as generate_stats.py: plain <rect>/<text>/<circle> only,
no <foreignObject>, so the cards actually paint when embedded via <img>.
Emits a dark and a light variant per repo for <picture> theme switching.
"""
import json
import os
import re
import sys
import textwrap
import urllib.request
from datetime import datetime, timezone

from theme import FONT, esc, get_theme

USERNAME = os.environ.get("STATS_USERNAME", "sheinafathurr1")
TOKEN = os.environ.get("GITHUB_TOKEN")
REPOS = ["portfolio", "e-football", "ideahub", "webtrain"]

API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": USERNAME,
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def relative_time(iso_str):
    then = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - then
    days = delta.days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def wrap_description(text, width=44, max_lines=2):
    if not text:
        return []
    return textwrap.wrap(text, width=width, max_lines=max_lines, placeholder="…")


def render_card(repo, theme_name="dark"):
    theme = get_theme(theme_name)
    name = repo["name"]
    description = repo.get("description") or "No description provided."
    language = repo.get("language") or "—"
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    updated = relative_time(repo["updated_at"]) if repo.get("updated_at") else ""

    width, height = 420, 150

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1" />',
        f'<circle cx="28" cy="34" r="5" fill="{theme["title"]}" fill-opacity="0.85" />',
        f'<text x="42" y="39" {FONT} font-size="16" font-weight="700" fill="{theme["title"]}">{esc(name)}</text>',
    ]

    lines = wrap_description(description)
    for i, line in enumerate(lines):
        y = 66 + i * 20
        parts.append(f'<text x="28" y="{y}" {FONT} font-size="12.5" fill="{theme["text"]}">{esc(line)}</text>')

    footer_y = height - 24
    parts.append(f'<line x1="28" y1="{footer_y - 20}" x2="{width - 28}" y2="{footer_y - 20}" stroke="{theme["border"]}" stroke-width="1" />')
    parts.append(f'<circle cx="32" cy="{footer_y}" r="4" fill="{theme["title"]}" fill-opacity="0.7" />')
    parts.append(f'<text x="42" y="{footer_y + 4}" {FONT} font-size="11.5" fill="{theme["text"]}">{esc(language)}</text>')
    parts.append(f'<text x="190" y="{footer_y + 4}" {FONT} font-size="11.5" fill="{theme["text"]}">&#9733; {stars}</text>')
    parts.append(f'<text x="250" y="{footer_y + 4}" {FONT} font-size="11.5" fill="{theme["text"]}">Forks {forks}</text>')
    parts.append(f'<text x="{width - 28}" y="{footer_y + 4}" {FONT} font-size="11.5" fill="{theme["text_dimmer"]}" text-anchor="end">Updated {esc(updated)}</text>')

    parts.append("</svg>")
    return "\n".join(p for p in parts if p)


def slug(name):
    return re.sub(r"[^a-z0-9-]", "", name.lower())


def main():
    os.makedirs("projects", exist_ok=True)
    for repo_name in REPOS:
        try:
            repo = get(f"{API}/repos/{USERNAME}/{repo_name}")
        except Exception as exc:  # noqa: BLE001
            print(f"::warning::Skipping {repo_name}: {exc}", file=sys.stderr)
            continue
        for theme_name in ("dark", "light"):
            svg = render_card(repo, theme_name=theme_name)
            out_path = f"projects/{slug(repo_name)}-{theme_name}.svg"
            with open(out_path, "w") as f:
                f.write(svg)
            print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
