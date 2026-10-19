"""Redraw the 3D graph's radar chart with counts that include private repos.

The action reads contributionsCollection, which folds private work into one
restricted total, so its per-type axes only ever count public activity. The
search API, given a token that can read the private repos, does not.

Without PROFILE_TOKEN, or if any search fails, the files are left as the
action drew them: public-only counts, never a broken image.
"""
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = os.environ.get("USERNAME", "PoyrazTahan")
TOKEN = os.environ.get("PROFILE_TOKEN", "")
SINCE = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

# Axis order as the action draws them, clockwise from the top.
QUERIES = {
    "commit": ("commits", f"author:{USER} author-date:>={SINCE}"),
    "issue": ("issues", f"author:{USER} type:issue created:>={SINCE}"),
    "pullreq": ("issues", f"author:{USER} type:pr created:>={SINCE}"),
    "review": ("issues", f"reviewed-by:{USER} type:pr created:>={SINCE}"),
    "repo": ("repositories", f"user:{USER} created:>={SINCE}"),
}
LABELS = {"commit": "Commit", "issue": "Issue", "pullreq": "PullReq", "review": "Review", "repo": "Repo"}
ANGLES = [-90 + 72 * i for i in range(5)]
UNIT = 31.2  # radius per decade: 1 -> 31.2, 10 -> 62.4, ... 10K -> 156


def search(kind: str, q: str) -> int:
    url = f"https://api.github.com/search/{kind}?per_page=1&q={urllib.parse.quote(q)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["total_count"]


def radius(n: int) -> float:
    # Matches the action: zero sits just inside the "1" ring.
    return UNIT * (1 + math.log10(n)) if n >= 1 else UNIT * 0.8


def points(counts: list[int]) -> str:
    out = []
    for n, a in zip(counts, ANGLES):
        r = radius(n)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        out.append(f"{x:.2f},{y:.2f}")
    return " ".join(out)


def patch(path: Path, counts: dict[str, int]) -> None:
    s = path.read_text()
    final = points([counts[k] for k in QUERIES])
    # Final shape, and the last frame of its grow-in animation.
    s = re.sub(r'(class="radar" points=")[^"]*', rf"\g<1>{final}", s, count=1)
    s = re.sub(r'(attributeName="points" values="[^;"]*;)[^"]*', rf"\g<1>{final}", s, count=1)
    # Hover tooltip on each axis label.
    for k, label in LABELS.items():
        s = re.sub(rf"(>{label}<title>)\d+(</title>)", rf"\g<1>{counts[k]}\g<2>", s, count=1)
    path.write_text(s)


if not TOKEN:
    print("PROFILE_TOKEN not set; keeping public-only radar")
    sys.exit(0)
try:
    counts = {k: search(kind, q) for k, (kind, q) in QUERIES.items()}
except Exception as e:  # expired token, rate limit, outage
    print(f"search failed ({e}); keeping public-only radar")
    sys.exit(0)

print("counts since", SINCE, counts)
for p in sorted(Path(sys.argv[1]).glob("*.svg")):
    patch(p, counts)
