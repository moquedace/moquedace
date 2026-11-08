"""Draw the contribution activity graph shown in the profile README.

Replaces github-readme-activity-graph.vercel.app, which went offline (HTTP 402)
in Oct 2026: contributions come straight from the GitHub GraphQL API and the
SVG is committed to the repository, so the README no longer depends on an
external image service. Standard library only.
"""

import datetime as dt
import json
import os
import urllib.request

USER = os.environ.get("GRAPH_USER", "moquedace")
DAYS = 31
OUT = os.environ.get("GRAPH_OUT", "assets/activity_graph.svg")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days():
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=DAYS - 1)
    body = json.dumps({
        "query": QUERY,
        "variables": {
            "login": USER,
            "from": f"{start}T00:00:00Z",
            "to": f"{today}T23:59:59Z",
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "activity-graph"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}
    days = [start + dt.timedelta(days=i) for i in range(DAYS)]
    return [(d, counts.get(d.isoformat(), 0)) for d in days]


def nice_max(v):
    # y-axis ceiling = 4 grid steps of 1, 2 or 5 x 10^k, so every label is an integer
    raw = max(1, -(-v // 4))
    k = 10 ** (len(str(raw)) - 1)
    for m in (1, 2, 5, 10):
        if raw <= m * k:
            return 4 * m * k
    return 40 * k


def build_svg(series):
    W, H = 1000, 360
    L, R, T, B = 56, 24, 64, 52
    pw, ph = W - L - R, H - T - B
    ymax = nice_max(max(c for _, c in series))
    n = len(series)

    def x(i):
        return L + pw * i / (n - 1)

    def y(c):
        return T + ph * (1 - c / ymax)

    pts = [(x(i), y(c)) for i, (_, c) in enumerate(series)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"M{L},{T + ph} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f" L{L + pw},{T + ph} Z"

    total = sum(c for _, c in series)
    first, last = series[0][0], series[-1][0]
    span = f"{first:%d %b %Y} – {last:%d %b %Y}"

    grid, ylab = [], []
    for k in range(5):
        v = ymax * k / 4
        gy = y(v)
        grid.append(f'<line class="grid" x1="{L}" y1="{gy:.1f}" x2="{L + pw}" y2="{gy:.1f}"/>')
        ylab.append(f'<text class="tick" x="{L - 10}" y="{gy + 4:.1f}" text-anchor="end">{v:g}</text>')

    xlab = []
    for i, (d, _) in enumerate(series):
        if i % 2 == 0 or i == n - 1:
            xlab.append(f'<text class="tick" x="{x(i):.1f}" y="{T + ph + 20}" text-anchor="middle">{d.day}</text>')
    months = []
    for i, (d, _) in enumerate(series):
        if i == 0 or d.day == 1:
            months.append(f'<text class="month" x="{x(i):.1f}" y="{T + ph + 40}" text-anchor="middle">{d:%b}</text>')

    dots = "".join(f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="3.5"/>' for px, py in pts)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{USER} contribution activity, {span}">
<style>
  .title {{ font: 600 18px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2328; }}
  .sub   {{ font: 400 13px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #59636e; }}
  .tick  {{ font: 400 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #59636e; }}
  .month {{ font: 600 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #59636e; }}
  .grid  {{ stroke: #d1d9e0; stroke-width: 1; }}
  .axis  {{ stroke: #9198a1; stroke-width: 1; }}
  .line  {{ fill: none; stroke: #2E86AB; stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }}
  .dot   {{ fill: #ffffff; stroke: #2E86AB; stroke-width: 2; }}
  @media (prefers-color-scheme: dark) {{
    .title {{ fill: #f0f6fc; }}
    .sub, .tick, .month {{ fill: #9198a1; }}
    .grid  {{ stroke: #3d444d; }}
    .axis  {{ stroke: #656c76; }}
    .dot   {{ fill: #0d1117; }}
  }}
</style>
<defs>
  <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2E86AB" stop-opacity="0.35"/>
    <stop offset="1" stop-color="#2E86AB" stop-opacity="0.02"/>
  </linearGradient>
</defs>
<text class="title" x="{L}" y="28">Contribution activity</text>
<text class="sub" x="{L}" y="48">{total} contributions · {span}</text>
<text class="sub" x="{W - R}" y="48" text-anchor="end">updated daily</text>
{"".join(grid)}
<line class="axis" x1="{L}" y1="{T + ph}" x2="{L + pw}" y2="{T + ph}"/>
<path d="{area}" fill="url(#fill)"/>
<polyline class="line" points="{line}"/>
{dots}
{"".join(ylab)}
{"".join(xlab)}
{"".join(months)}
</svg>
'''


if __name__ == "__main__":
    series = fetch_days()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_svg(series))
    print(f"{OUT}: {sum(c for _, c in series)} contributions over {len(series)} days")
