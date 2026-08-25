#!/usr/bin/env python3
"""Generate a self-hosted, monochrome achievement badge grid as plain SVG.

Replaces the old github-profile-trophy.vercel.app widget (dropped for
reliability reasons) with a small set of real metrics rendered as chips:
years on GitHub, public repos, followers, contributions in the past
year, longest contribution streak, and total stars. Plain <rect>/<text>
only, no <foreignObject> — same approach as the other generated cards.
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone

from theme import FONT, esc, get_theme

USERNAME = os.environ.get("STATS_USERNAME", "sheinafathurr1")
TOKEN = os.environ.get("GITHUB_TOKEN")

API = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": USERNAME,
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


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


def fetch_contribution_data():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def longest_streak(days):
    best = current = 0
    for day in days:
        if day["contributionCount"] > 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def main():
    user = get(f"{API}/users/{USERNAME}")
    repos = get_all_repos(USERNAME)
    owned = [r for r in repos if not r.get("fork")]
    total_stars = sum(r.get("stargazers_count", 0) for r in owned)

    created = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    years_active = max((datetime.now(timezone.utc) - created).days // 365, 0)

    calendar = fetch_contribution_data()
    days = [d for week in calendar["weeks"] for d in week["contributionDays"]]

    chips = [
        (f"{years_active}+", "Years on GitHub"),
        (str(user.get("public_repos", len(owned))), "Public Repos"),
        (str(user.get("followers", 0)), "Followers"),
        (str(calendar["totalContributions"]), "Contributions (1y)"),
        (str(longest_streak(days)), "Longest Streak (days)"),
        (str(total_stars), "Total Stars"),
    ]

    for theme_name in ("dark", "light"):
        svg = render_svg(chips, theme_name=theme_name)
        with open(f"achievements-{theme_name}.svg", "w") as f:
            f.write(svg)
        print(f"wrote achievements-{theme_name}.svg")


def render_svg(chips, theme_name="dark"):
    theme = get_theme(theme_name)
    width = 800
    cols = 3
    pad_x, pad_top = 32, 58
    gap = 16
    chip_w = (width - pad_x * 2 - gap * (cols - 1)) / cols
    chip_h = 78
    rows = (len(chips) + cols - 1) // cols
    height = pad_top + rows * chip_h + (rows - 1) * gap + 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" viewBox="0 0 {width} {height:.0f}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1:.0f}" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1" />',
        f'<text x="32" y="42" {FONT} font-size="18" font-weight="600" fill="{theme["title"]}">Achievements</text>',
        f'<line x1="32" y1="58" x2="{width - 32}" y2="58" stroke="{theme["border"]}" stroke-width="1" />',
    ]

    for i, (value, label) in enumerate(chips):
        col = i % cols
        row = i // cols
        x = pad_x + col * (chip_w + gap)
        y = pad_top + 16 + row * (chip_h + gap)

        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{chip_w:.1f}" height="{chip_h}" rx="8" '
            f'fill="{theme["bar_track"]}" stroke="{theme["border"]}" stroke-width="1" />'
        )
        cx = x + chip_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 34:.1f}" {FONT} font-size="24" font-weight="700" '
            f'fill="{theme["title"]}" text-anchor="middle">{esc(value)}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 58:.1f}" {FONT} font-size="11.5" '
            f'fill="{theme["text"]}" text-anchor="middle">{esc(label)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Failed to generate achievements.svg: {exc}", file=sys.stderr)
        raise
