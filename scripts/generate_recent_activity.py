#!/usr/bin/env python3
"""Generate a self-hosted, monochrome "recent activity" timeline as SVG.

Unlike stats/achievements/activity (which are aggregate numbers), this
pulls the user's public events feed and renders the last few concrete
actions (pushes, PRs, issues, stars...) as a readable timeline. Plain
<rect>/<text>/<circle> only, no <foreignObject>.
"""
import json
import os
import sys
import urllib.request

from theme import FONT, esc, get_theme, relative_time

USERNAME = os.environ.get("STATS_USERNAME", "sheinafathurr1")
TOKEN = os.environ.get("GITHUB_TOKEN")
MAX_ITEMS = 5

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


def describe(event):
    kind = event["type"]
    repo = event["repo"]["name"]

    if kind == "PushEvent":
        payload = event["payload"]
        n = payload.get("size", len(payload.get("commits", [])))
        if n == 0:
            # A merge/ref update with no new distinct commits (e.g. a
            # squash or fast-forward merge) still fires a PushEvent.
            return f"Updated {repo}"
        commit_word = "commit" if n == 1 else "commits"
        return f"Pushed {n} {commit_word} to {repo}"

    if kind == "PullRequestEvent":
        action = event["payload"].get("action", "updated")
        return f"{action.capitalize()} a pull request in {repo}"

    if kind == "IssuesEvent":
        action = event["payload"].get("action", "updated")
        return f"{action.capitalize()} an issue in {repo}"

    if kind == "IssueCommentEvent":
        return f"Commented on an issue in {repo}"

    if kind == "PullRequestReviewEvent":
        return f"Reviewed a pull request in {repo}"

    if kind == "CreateEvent":
        ref_type = event["payload"].get("ref_type", "repository")
        return f"Created {ref_type} in {repo}" if ref_type != "repository" else f"Created {repo}"

    if kind == "WatchEvent":
        return f"Starred {repo}"

    if kind == "ForkEvent":
        return f"Forked {repo}"

    if kind == "ReleaseEvent":
        return f"Published a release in {repo}"

    if kind == "DeleteEvent":
        ref_type = event["payload"].get("ref_type", "branch")
        return f"Deleted a {ref_type} in {repo}"

    return f"{kind.replace('Event', '')} in {repo}"


def fetch_recent_items():
    events = get(f"{API}/users/{USERNAME}/events/public?per_page=30")
    items = []
    for event in events:
        try:
            text = describe(event)
        except Exception:  # noqa: BLE001
            continue
        items.append((text, event["created_at"]))
        if len(items) >= MAX_ITEMS:
            break
    return items


def render_svg(items, theme_name="dark"):
    theme = get_theme(theme_name)
    width = 800
    pad_x, pad_top = 32, 58
    row_h = 38
    height = pad_top + max(len(items), 1) * row_h + 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}" stroke-width="1" />',
        f'<text x="32" y="42" {FONT} font-size="18" font-weight="600" fill="{theme["title"]}">Recent Activity</text>',
        f'<line x1="32" y1="58" x2="{width - 32}" y2="58" stroke="{theme["border"]}" stroke-width="1" />',
    ]

    if not items:
        parts.append(
            f'<text x="{pad_x}" y="{pad_top + 24}" {FONT} font-size="13" fill="{theme["text"]}">No recent public activity</text>'
        )
    else:
        for i, (text, created_at) in enumerate(items):
            y = pad_top + 22 + i * row_h
            when = relative_time(created_at)
            parts.append(f'<circle cx="{pad_x}" cy="{y - 4}" r="3.5" fill="{theme["bar_fill"]}" fill-opacity="0.8" />')
            if i < len(items) - 1:
                parts.append(
                    f'<line x1="{pad_x}" y1="{y + 2}" x2="{pad_x}" y2="{y + row_h - 6}" stroke="{theme["border"]}" stroke-width="1" />'
                )
            parts.append(
                f'<text x="{pad_x + 16}" y="{y}" {FONT} font-size="13" fill="{theme["text"]}">{esc(text)}</text>'
            )
            parts.append(
                f'<text x="{width - pad_x}" y="{y}" {FONT} font-size="11.5" fill="{theme["text_dimmer"]}" text-anchor="end">{esc(when)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    items = fetch_recent_items()
    for theme_name in ("dark", "light"):
        svg = render_svg(items, theme_name=theme_name)
        with open(f"activity-feed-{theme_name}.svg", "w") as f:
            f.write(svg)
        print(f"wrote activity-feed-{theme_name}.svg")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Failed to generate activity-feed.svg: {exc}", file=sys.stderr)
        raise
