#!/usr/bin/env python3
"""Generate a self-hosted, monochrome GitHub stats card as a plain SVG.

Plain <rect>/<text> only (no <foreignObject>), so it renders correctly
when embedded via <img> in a GitHub README, unlike HTML-in-SVG generators.
Uses the workflow's own GITHUB_TOKEN, so it isn't subject to the shared
rate limits that third-party public stats widgets run into.

Emits one file per theme (stats-dark.svg / stats-light.svg) so the
README can switch between them with <picture prefers-color-scheme>.
"""
import json
import os
import sys
import urllib.request

from theme import FONT, esc, get_theme

USERNAME = os.environ.get("STATS_USERNAME", "sheinafathurr1")
TOKEN = os.environ.get("GITHUB_TOKEN")

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


def get_all_repos(username):
    repos = []
    page = 1
    while True:
        url = f"{API}/users/{username}/repos?type=owner&per_page=100&page={page}"
        batch = get(url)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def main():
    user = get(f"{API}/users/{USERNAME}")
    repos = get_all_repos(USERNAME)
    owned = [r for r in repos if not r.get("fork")]

    total_stars = sum(r.get("stargazers_count", 0) for r in owned)
    total_forks = sum(r.get("forks_count", 0) for r in owned)
    public_repos = user.get("public_repos", len(owned))
    followers = user.get("followers", 0)

    lang_bytes = {}
    for r in owned:
        try:
            langs = get(r["languages_url"])
        except Exception:
            continue
        for lang, count in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + count

    total_lang_bytes = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:6]

    stats = [
        ("Public Repos", public_repos),
        ("Followers", followers),
        ("Total Stars", total_stars),
        ("Total Forks", total_forks),
    ]
    languages = [(name, count / total_lang_bytes) for name, count in top_langs]

    for theme_name in ("dark", "light"):
        svg = render_svg(stats=stats, languages=languages, theme_name=theme_name)
        with open(f"stats-{theme_name}.svg", "w") as f:
            f.write(svg)


def render_svg(stats, languages, theme_name="dark"):
    theme = get_theme(theme_name)
    width = 800
    height = 300

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    parts.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1" />'
    )
    parts.append(
        f'<text x="32" y="42" {FONT} font-size="18" font-weight="600" fill="{theme["title"]}">GitHub Stats</text>'
    )
    parts.append(f'<line x1="32" y1="58" x2="{width - 32}" y2="58" stroke="{theme["border"]}" stroke-width="1" />')

    # Stat boxes
    box_w = (width - 64) / len(stats)
    for i, (label, value) in enumerate(stats):
        cx = 32 + box_w * i + box_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="130" {FONT} font-size="30" font-weight="700" '
            f'fill="{theme["title"]}" text-anchor="middle">{esc(value)}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="156" {FONT} font-size="13" '
            f'fill="{theme["text"]}" text-anchor="middle">{esc(label)}</text>'
        )
        if i > 0:
            x = 32 + box_w * i
            parts.append(f'<line x1="{x:.1f}" y1="90" x2="{x:.1f}" y2="170" stroke="{theme["border"]}" stroke-width="1" />')

    parts.append(f'<line x1="32" y1="190" x2="{width - 32}" y2="190" stroke="{theme["border"]}" stroke-width="1" />')
    parts.append(
        f'<text x="32" y="216" {FONT} font-size="14" font-weight="600" fill="{theme["title"]}">Top Languages</text>'
    )

    # Language bars
    bar_x = 32
    bar_y = 232
    bar_w = width - 64
    bar_h = 10
    if languages:
        x = bar_x
        parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{theme["bar_track"]}" />')
        for i, (name, pct) in enumerate(languages):
            seg_w = max(bar_w * pct, 2)
            opacity = max(1.0 - i * 0.14, 0.28)
            parts.append(
                f'<rect x="{x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" '
                f'fill="{theme["bar_fill"]}" fill-opacity="{opacity:.2f}" />'
            )
            x += seg_w

        legend_y = bar_y + 34
        col_w = bar_w / 3
        for i, (name, pct) in enumerate(languages):
            col = i % 3
            row = i // 3
            lx = bar_x + col * col_w
            ly = legend_y + row * 26
            opacity = max(1.0 - i * 0.14, 0.28)
            parts.append(f'<circle cx="{lx + 6}" cy="{ly - 4}" r="5" fill="{theme["bar_fill"]}" fill-opacity="{opacity:.2f}" />')
            parts.append(
                f'<text x="{lx + 18}" y="{ly}" {FONT} font-size="12" fill="{theme["text"]}">'
                f'{esc(name)} {pct * 100:.1f}%</text>'
            )
    else:
        parts.append(
            f'<text x="{bar_x}" y="{bar_y + 10}" {FONT} font-size="12" fill="{theme["text"]}">No language data</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Failed to generate stats.svg: {exc}", file=sys.stderr)
        raise
