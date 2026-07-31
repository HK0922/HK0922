"""
Pulls contribution history, repo languages, and repo/star counts straight
from GitHub's GraphQL API and writes a normalized data/github_stats.json
that the *_card.py scripts read from.

Auth: uses the login passed in (or $GITHUB_REPOSITORY_OWNER, which Actions
sets automatically) together with $GITHUB_TOKEN. The default Actions
GITHUB_TOKEN is enough here because we query `user(login: ...)` rather than
`viewer` -- we're reading PUBLIC data about a named user, not acting as
that user, so no personal access token / extra scopes are required.

Note: contributionsCollection on a user you're not authenticated *as* only
returns public contributions (private-repo commits are excluded). That's
the same limitation every public "profile stats" card has.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import random
import sys
import urllib.request

API_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: [OWNER], isFork: false,
                  orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def fetch(login: str, token: str) -> dict:
    to = dt.datetime.now(dt.timezone.utc)
    frm = to - dt.timedelta(days=365)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    body = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": frm.strftime(fmt),
            "to": to.strftime(fmt),
        },
    }).encode()

    req = urllib.request.Request(
        API_URL, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": login,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())

    if "errors" in payload:
        raise RuntimeError(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def compute_streaks(days: list[dict]) -> tuple[int, int]:
    """Return (current_streak, longest_streak) in days, walking the
    flattened contribution-day list in chronological order."""
    longest = current = 0
    running = 0
    today = dt.date.today().isoformat()
    for d in days:
        if d["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["contributionCount"] > 0:
            current += 1
        else:
            break
    return current, longest


def normalize(raw: dict) -> dict:
    cal = raw["contributionsCollection"]["contributionCalendar"]
    days = [day for week in cal["weeks"] for day in week["contributionDays"]]
    current_streak, longest_streak = compute_streaks(days)

    lang_bytes: dict[str, int] = {}
    total_stars = 0
    for repo in raw["repositories"]["nodes"]:
        total_stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            lang_bytes[edge["node"]["name"]] = (
                lang_bytes.get(edge["node"]["name"], 0) + edge["size"]
            )

    total_bytes = sum(lang_bytes.values()) or 1
    top_languages = [
        {"name": name, "percent": round(size / total_bytes * 100, 1)}
        for name, size in sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:6]
    ]

    return {
        "login": raw.get("name") or "",
        "followers": raw["followers"]["totalCount"],
        "total_repos": raw["repositories"]["totalCount"],
        "total_stars": total_stars,
        "total_contributions": cal["totalContributions"],
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "top_languages": top_languages,
        "calendar_weeks": [
            [d["contributionCount"] for d in week["contributionDays"]]
            for week in cal["weeks"]
        ],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat() + "Z",
    }


def mock_data() -> dict:
    """Synthetic data so the card generators can be developed/tested
    before secrets/tokens are wired up in the target repo."""
    random.seed(7)
    weeks = [[random.choice([0, 0, 0, 1, 2, 3, 4, 6]) for _ in range(7)]
              for _ in range(52)]
    flat = [c for w in weeks for c in w]
    return {
        "login": "Sample User",
        "followers": 128,
        "total_repos": 34,
        "total_stars": 261,
        "total_contributions": sum(flat),
        "current_streak": 9,
        "longest_streak": 41,
        "top_languages": [
            {"name": "Python", "percent": 46.2},
            {"name": "TypeScript", "percent": 21.8},
            {"name": "Jupyter Notebook", "percent": 14.5},
            {"name": "C++", "percent": 9.1},
            {"name": "Shell", "percent": 5.4},
            {"name": "HTML", "percent": 3.0},
        ],
        "calendar_weeks": weeks,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat() + "Z",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--out", default="data/github_stats.json")
    ap.add_argument("--mock", action="store_true",
                     help="write synthetic sample data instead of calling the API")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    if args.mock:
        data = mock_data()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or not args.login:
            sys.exit("GITHUB_TOKEN and a login (--login or $GITHUB_REPOSITORY_OWNER) "
                      "are required. Use --mock to test without them.")
        data = normalize(fetch(args.login, token))

    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
