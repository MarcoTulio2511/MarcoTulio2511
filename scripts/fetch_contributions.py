#!/usr/bin/env python3
"""
fetch_contributions.py — Step 5a of the heatmap pipeline.

No GraphQL API, no personal access token. GitHub serves the
contribution calendar as public HTML at
https://github.com/users/<username>/contributions — the same
fragment the profile page itself uses. We fetch it with requests,
parse each day cell with BeautifulSoup, and write a JSON file with
the raw days plus a few derived stats (current streak, longest
streak, best day, monthly totals) for the info card / heatmap footer
to use.

Usage:
    python scripts/fetch_contributions.py [username]
Default username: MarcoTulio2511
Writes: data/contributions.json
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "MarcoTulio2511"
UA = "Mozilla/5.0 (compatible; profile-readme-bot/1.0; +https://github.com)"


def fetch_contribution_days(username: str) -> list[dict]:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Tooltip text ("5 contributions on October 3rd." / "No contributions on
    # October 3rd.") lives in <tool-tip for="cell-id">; the count-free
    # data-level attribute alone isn't precise enough for streak/day stats.
    tooltip_by_id = {}
    for tip in soup.select("tool-tip"):
        for_id = tip.get("for")
        if for_id:
            tooltip_by_id[for_id] = tip.get_text(strip=True)

    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        date = td.get("data-date")
        level = int(td.get("data-level") or 0)
        tip_text = tooltip_by_id.get(td.get("id"), "")
        count = _parse_count(tip_text)
        days.append({"date": date, "level": level, "count": count})

    days.sort(key=lambda d: d["date"])
    return days


def _parse_count(tip_text: str) -> int:
    if not tip_text:
        return 0
    if tip_text.lower().startswith("no contributions"):
        return 0
    m = re.match(r"(\d+)\s+contribution", tip_text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def derive_stats(days: list[dict]) -> dict:
    longest = current = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    # current streak = run ending at the last day with activity, through today
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        else:
            break

    best_day = max(days, key=lambda d: d["count"], default=None)
    monthly = defaultdict(int)
    for d in days:
        monthly[d["date"][:7]] += d["count"]

    return {
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best_day["date"], "count": best_day["count"]} if best_day else None,
        "monthly_totals": dict(sorted(monthly.items())),
    }


def main(username: str) -> None:
    days = fetch_contribution_days(username)
    total = sum(d["count"] for d in days)
    stats = derive_stats(days)

    payload = {
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start_date": days[0]["date"] if days else None,
        "end_date": days[-1]["date"] if days else None,
        "total_contributions": total,
        "days": days,
        "stats": stats,
    }

    out_path = Path("data/contributions.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_path} ({len(days)} days, {total} contributions)")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME
    main(username)
