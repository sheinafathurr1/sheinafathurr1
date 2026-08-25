#!/usr/bin/env python3
"""Generate a monochrome monthly commit-activity bar chart as a plain SVG.

Pulls the public contribution calendar via the GitHub GraphQL API and
aggregates it into the last 12 calendar months. Distinct from the daily
contribution-snake grid: this shows the macro month-over-month trend.
"""
import json
import os
import sys
import urllib.request
from calendar import month_abbr
from datetime import date, datetime, timezone

from theme import FONT, esc, get_theme

USERNAME = os.environ.get("STATS_USERNAME", "sheinafathurr1")
TOKEN = os.environ.get("GITHUB_TOKEN")

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
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


def fetch_contribution_days():
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

    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        days.extend(week["contributionDays"])
    return days


def monthly_totals(days, months_back=12):
    today = date.today()
    buckets = []
    year, month = today.year, today.month
    for _ in range(months_back):
        buckets.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    buckets.reverse()

    totals = {key: 0 for key in buckets}
    for day in days:
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        key = (d.year, d.month)
        if key in totals:
            totals[key] += day["contributionCount"]

    return [(f"{month_abbr[m]}", totals[(y, m)]) for (y, m) in buckets]


def render_svg(months, theme_name="dark"):
    theme = get_theme(theme_name)
    width, height = 800, 220
    pad_x, pad_top, pad_bottom = 32, 58, 46

    max_count = max((c for _, c in months), default=0) or 1
    chart_w = width - pad_x * 2
    chart_h = height - pad_top - pad_bottom
    col_w = chart_w / len(months)
    bar_w = col_w * 0.5

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1" />',
        f'<text x="32" y="42" {FONT} font-size="18" font-weight="600" fill="{theme["title"]}">Commit Activity</text>',
        f'<line x1="32" y1="58" x2="{width - 32}" y2="58" stroke="{theme["border"]}" stroke-width="1" />',
        f'<line x1="{pad_x}" y1="{pad_top + chart_h}" x2="{width - pad_x}" y2="{pad_top + chart_h}" stroke="{theme["border"]}" stroke-width="1" />',
    ]

    for i, (label, count) in enumerate(months):
        bar_h = (count / max_count) * (chart_h - 20) if max_count else 0
        bar_h = max(bar_h, 2 if count > 0 else 0)
        x = pad_x + col_w * i + (col_w - bar_w) / 2
        y = pad_top + chart_h - bar_h
        opacity = 0.35 + 0.65 * (count / max_count if max_count else 0)

        if count > 0:
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" {FONT} font-size="11" '
                f'fill="{theme["text_dim"]}" text-anchor="middle">{count}</text>'
            )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="3" '
            f'fill="{theme["bar_fill"]}" fill-opacity="{opacity:.2f}" />'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{pad_top + chart_h + 20}" {FONT} font-size="12" '
            f'fill="{theme["text"]}" text-anchor="middle">{esc(label)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    days = fetch_contribution_days()
    months = monthly_totals(days)
    for theme_name in ("dark", "light"):
        svg = render_svg(months, theme_name=theme_name)
        with open(f"activity-{theme_name}.svg", "w") as f:
            f.write(svg)
        print(f"wrote activity-{theme_name}.svg")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Failed to generate activity.svg: {exc}", file=sys.stderr)
        raise
