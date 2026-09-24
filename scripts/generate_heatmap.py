#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = "Aurezhan"
TOKEN = os.environ["GITHUB_TOKEN"]
YEAR = datetime.now(timezone.utc).year
FROM = f"{YEAR}-01-01T00:00:00Z"
TO = f"{YEAR}-12-31T23:59:59Z"

query = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {"login": USERNAME, "from": FROM, "to": TO},
}).encode()

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Aurezhan-profile-heatmap",
    },
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode())

if "errors" in result:
    raise RuntimeError(result["errors"])

calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

counts = sorted(
    day["contributionCount"]
    for week in weeks
    for day in week["contributionDays"]
    if day["contributionCount"] > 0
)

def percentile(values, p):
    if not values:
        return 1
    i = min(len(values) - 1, max(0, int((len(values) - 1) * p)))
    return values[i]

q1 = percentile(counts, 0.25)
q2 = percentile(counts, 0.50)
q3 = percentile(counts, 0.75)

def color(count):
    if count == 0:
        return "#161018"
    if count <= q1:
        return "#43131d"
    if count <= q2:
        return "#741827"
    if count <= q3:
        return "#b62139"
    return "#ff3b5c"

cell = 14
gap = 4
step = cell + gap
left = 46
top = 42
width = max(1040, left + len(weeks) * step + 18)
height = 196

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
    '<style>text{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif}</style>',
    f'<text x="0" y="16" fill="#c9d1d9" font-size="14" font-weight="600">{total} contributions in {YEAR}</text>',
]

# Month labels
last_month = None
for wi, week in enumerate(weeks):
    if not week["contributionDays"]:
        continue
    first = week["contributionDays"][0]
    dt = datetime.strptime(first["date"], "%Y-%m-%d")
    month = dt.strftime("%b")
    if dt.month != last_month and dt.day <= 7:
        x = left + wi * step
        parts.append(f'<text x="{x}" y="35" fill="#8b949e" font-size="11">{month}</text>')
        last_month = dt.month

# Weekday labels
for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
    y = top + row * step + 11
    parts.append(f'<text x="0" y="{y}" fill="#8b949e" font-size="10">{label}</text>')

for wi, week in enumerate(weeks):
    for day in week["contributionDays"]:
        x = left + wi * step
        y = top + day["weekday"] * step
        c = day["contributionCount"]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{color(c)}"><title>{day["date"]}: {c} contributions</title></rect>'
        )

# Legend
legend_x = width - 178
legend_y = height - 24
parts.append(f'<text x="{legend_x}" y="{legend_y+10}" fill="#8b949e" font-size="10">Less</text>')
legend_colors = ["#161018", "#43131d", "#741827", "#b62139", "#ff3b5c"]
for i, c in enumerate(legend_colors):
    parts.append(
        f'<rect x="{legend_x + 34 + i * 17}" y="{legend_y}" width="12" height="12" rx="3" fill="{c}"/>'
    )
parts.append(f'<text x="{legend_x + 124}" y="{legend_y+10}" fill="#8b949e" font-size="10">More</text>')
parts.append("</svg>")

os.makedirs("assets", exist_ok=True)
with open("assets/contribution-heatmap.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
