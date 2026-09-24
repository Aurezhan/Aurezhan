#!/usr/bin/env python3
import html
import os
import re
import urllib.request
from datetime import datetime, timezone

USERNAME = "Aurezhan"
YEAR = datetime.now(timezone.utc).year

url = (
    f"https://github.com/users/{USERNAME}/contributions"
    f"?from={YEAR}-01-01&to={YEAR}-12-31"
)

req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 Aurezhan-profile-heatmap",
        "Accept": "text/html,application/xhtml+xml",
    },
)

with urllib.request.urlopen(req) as response:
    page = response.read().decode("utf-8", errors="replace")

# GitHub's public contribution page exposes one cell per day.
# We only need date + intensity level (0..4), which avoids requiring a PAT.
cells = re.findall(
    r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="([0-4])"[^>]*?>',
    page,
)

# GitHub has changed attribute ordering before, so support the reverse order too.
if not cells:
    reverse = re.findall(
        r'<td[^>]*?data-level="([0-4])"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?>',
        page,
    )
    cells = [(date, level) for level, date in reverse]

if not cells:
    raise RuntimeError("Could not parse GitHub contribution calendar.")

# Try to capture the public total shown by GitHub.
total_match = re.search(
    r'([\d,]+)\s+contributions?\s+in\s+' + str(YEAR),
    html.unescape(page),
    re.IGNORECASE,
)
total_text = total_match.group(1) if total_match else None

days = {}
for date_str, level in cells:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if dt.year == YEAR:
        days[date_str] = int(level)

# Build Sunday-based calendar columns like GitHub.
jan1 = datetime(YEAR, 1, 1)
dec31 = datetime(YEAR, 12, 31)

# Python Monday=0..Sunday=6 -> Sunday=0..Saturday=6
def sunday_index(dt):
    return (dt.weekday() + 1) % 7

start = jan1
while sunday_index(start) != 0:
    from datetime import timedelta
    start -= timedelta(days=1)

from datetime import timedelta
end = dec31
while sunday_index(end) != 6:
    end += timedelta(days=1)

weeks = []
cursor = start
while cursor <= end:
    week = []
    for _ in range(7):
        date_str = cursor.strftime("%Y-%m-%d")
        week.append((cursor, days.get(date_str, 0) if cursor.year == YEAR else None))
        cursor += timedelta(days=1)
    weeks.append(week)

colors = {
    0: "#161018",
    1: "#43131d",
    2: "#741827",
    3: "#b62139",
    4: "#ff3b5c",
}

cell = 14
gap = 4
step = cell + gap
left = 48
top = 46
width = max(1040, left + len(weeks) * step + 20)
height = 202

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
    '<style>text{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif}</style>',
]

if total_text:
    parts.append(
        f'<text x="0" y="16" fill="#c9d1d9" font-size="14" font-weight="600">'
        f'{total_text} contributions in {YEAR}</text>'
    )
else:
    parts.append(
        f'<text x="0" y="16" fill="#c9d1d9" font-size="14" font-weight="600">'
        f'Contributions in {YEAR}</text>'
    )

# Month labels
last_month = None
for wi, week in enumerate(weeks):
    visible = [dt for dt, level in week if dt.year == YEAR]
    if not visible:
        continue
    dt = visible[0]
    if dt.month != last_month and dt.day <= 7:
        parts.append(
            f'<text x="{left + wi * step}" y="37" fill="#8b949e" font-size="11">'
            f'{dt.strftime("%b")}</text>'
        )
        last_month = dt.month

for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
    parts.append(
        f'<text x="0" y="{top + row * step + 11}" fill="#8b949e" font-size="10">{label}</text>'
    )

for wi, week in enumerate(weeks):
    for row, (dt, level) in enumerate(week):
        if level is None:
            continue
        x = left + wi * step
        y = top + row * step
        date_str = dt.strftime("%Y-%m-%d")
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{colors[level]}"><title>{date_str} · level {level}</title></rect>'
        )

legend_x = width - 172
legend_y = height - 23
parts.append(f'<text x="{legend_x}" y="{legend_y+10}" fill="#8b949e" font-size="10">Less</text>')
for i in range(5):
    parts.append(
        f'<rect x="{legend_x + 34 + i * 17}" y="{legend_y}" width="12" height="12" '
        f'rx="3" fill="{colors[i]}"/>'
    )
parts.append(f'<text x="{legend_x + 123}" y="{legend_y+10}" fill="#8b949e" font-size="10">More</text>')
parts.append("</svg>")

os.makedirs("assets", exist_ok=True)
with open("assets/contribution-heatmap.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
