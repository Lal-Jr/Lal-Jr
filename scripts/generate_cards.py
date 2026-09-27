#!/usr/bin/env python3
"""Generate the activity graph and stats card for the profile README.

Reads only public GitHub data, writes two SVGs into assets/. No third-party
service: the cards keep working as long as GitHub does.
"""
import json, os, re, sys, urllib.request
from datetime import date, datetime

USER = os.environ.get("GH_USER", "Lal-Jr")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

ZINC950, ZINC900, ZINC800 = "#09090b", "#18181b", "#27272a"
ZINC500, ZINC400, ZINC300 = "#71717a", "#a1a1aa", "#d4d4d8"
EMERALD, YELLOW = "#34d399", "#facc15"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Go": "#00ADD8",
    "Python": "#3572A5", "C++": "#f34b7d", "HTML": "#e34c26", "CSS": "#563d7c",
    "Shell": "#89e051", "Java": "#b07219", "Ruby": "#701516", "Rust": "#dea584",
}


def get(url, token=None, html=False):
    req = urllib.request.Request(url, headers={
        "User-Agent": "profile-cards",
        "Accept": "text/html" if html else "application/vnd.github+json",
    })
    if token and not html:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
    return raw if html else json.loads(raw)


def contributions(user):
    """Daily contribution counts from the public profile calendar."""
    h = get(f"https://github.com/users/{user}/contributions", html=True)
    cells = {}
    for td in re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', h):
        d = re.search(r'data-date="([\d-]+)"', td)
        i = re.search(r'id="([^"]+)"', td)
        if d and i:
            cells[i.group(1)] = d.group(1)
    tips = {}
    for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', h):
        t = m.group(2).strip()
        tips[m.group(1)] = 0 if t.startswith("No") else int(re.match(r"(\d+)", t).group(1))
    return sorted((d, tips.get(i, 0)) for i, d in cells.items())


def streaks(days):
    cur = best = 0
    for _, c in days:
        cur = cur + 1 if c else 0
        best = max(best, cur)
    tail = 0
    for _, c in reversed(days):
        if c:
            tail += 1
        else:
            break
    return tail, best


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def frame(w, h, parts):
    """Card shell in the banner's style."""
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">']
    s.append(f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
             f'<stop offset="0" stop-color="{ZINC950}"/><stop offset="1" stop-color="{ZINC900}"/></linearGradient></defs>')
    s.append(f'<rect width="{w}" height="{h}" rx="14" fill="url(#bg)"/>')
    for gx in range(0, w, 22):
        s.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{h}" stroke="{ZINC800}" stroke-width="0.6" opacity="0.35"/>')
    for gy in range(0, h, 22):
        s.append(f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke="{ZINC800}" stroke-width="0.6" opacity="0.35"/>')
    s += parts
    for cx, cy in [(22, 22), (w - 22, 22), (22, h - 22), (w - 22, h - 22)]:
        s.append(f'<rect x="{cx-3}" y="{cy-3}" width="6" height="6" fill="{EMERALD}" opacity="0.9"/>')
    s.append("</svg>")
    return "\n".join(s)


def activity_card(days):
    W, H = 880, 240
    L, R, T, B = 48, 28, 52, 42
    # aggregate into weeks so the line reads at this width
    weeks, bucket = [], []
    for d, c in days:
        bucket.append(c)
        if len(bucket) == 7:
            weeks.append(sum(bucket)); bucket = []
    if bucket:
        weeks.append(sum(bucket))
    peak = max(weeks) or 1
    iw, ih = W - L - R, H - T - B

    def pt(i, v):
        x = L + (iw * i / max(1, len(weeks) - 1))
        y = T + ih - (ih * v / peak)
        return x, y

    pts = [pt(i, v) for i, v in enumerate(weeks)]
    line = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = line + f" L {pts[-1][0]:.1f},{T+ih} L {pts[0][0]:.1f},{T+ih} Z"

    p = []
    p.append(f'<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{EMERALD}" stop-opacity="0.35"/>'
             f'<stop offset="1" stop-color="{EMERALD}" stop-opacity="0"/></linearGradient></defs>')
    p.append(f'<text x="{L}" y="30" font-family="{MONO}" font-size="13" letter-spacing="1.6" fill="{ZINC300}">'
             f'contributions, past year</text>')
    p.append(f'<text x="{W-R}" y="30" text-anchor="end" font-family="{MONO}" font-size="13" fill="{ZINC500}">'
             f'peak {peak}/week</text>')
    # baseline + gridlines
    for frac in (0.0, 0.5, 1.0):
        y = T + ih - ih * frac
        p.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{ZINC800}" stroke-width="1"/>')
        p.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-family="{MONO}" font-size="10" '
                 f'fill="{ZINC500}">{int(peak*frac)}</text>')
    p.append(f'<path d="{area}" fill="url(#fade)"/>')
    p.append(f'<path d="{line}" fill="none" stroke="{EMERALD}" stroke-width="2.2" '
             f'stroke-linejoin="round" stroke-linecap="round"/>')
    # mark the busiest week
    bi = weeks.index(peak)
    bx, by = pt(bi, peak)
    p.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="{YELLOW}"/>')
    # month ticks
    for i, (d, _) in enumerate(days):
        if d.endswith("-01") and i // 7 < len(weeks):
            x = L + (iw * (i // 7) / max(1, len(weeks) - 1))
            label = datetime.strptime(d, "%Y-%m-%d").strftime("%b")
            p.append(f'<text x="{x:.1f}" y="{H-16}" text-anchor="middle" font-family="{MONO}" '
                     f'font-size="10" fill="{ZINC500}">{label}</text>')
    return frame(W, H, p)


def language_bytes(repos, user):
    """Sum bytes per language across repos.

    GitHub labels a repo by its single largest language, which hides a Go
    backend sitting inside a mostly-TypeScript repo. Bytes tell the truth.
    """
    token = os.environ.get("GITHUB_TOKEN")
    totals = {}
    for r in repos:
        try:
            langs = get(f"https://api.github.com/repos/{user}/{r['name']}/languages", token)
        except Exception:
            langs = {r["language"]: 1} if r.get("language") else {}
        tot = sum(langs.values())
        if not tot:
            continue
        # Average each repo's composition rather than summing raw bytes: one repo
        # with a committed vendor bundle would otherwise swamp everything else.
        for lang, n in langs.items():
            totals[lang] = totals.get(lang, 0) + (n / tot)
    return totals


def stats_card(days, repos, user):
    W, H = 880, 240
    total = sum(c for _, c in days)
    active = sum(1 for _, c in days if c)
    cur, best = streaks(days)
    stars = sum(r["stargazers_count"] for r in repos)
    langs = language_bytes(repos, user)
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    tot_l = sum(n for _, n in top) or 1

    p = []
    p.append(f'<text x="48" y="38" font-family="{MONO}" font-size="13" letter-spacing="1.6" '
             f'fill="{ZINC300}">the numbers, such as they are</text>')
    figures = [(str(total), "contributions"), (str(active), "active days"),
               (f"{best}", "longest streak"), (str(len(repos)), "public repos"),
               (str(stars), "stars earned")]
    x = 48
    for val, label in figures:
        p.append(f'<text x="{x}" y="92" font-family="{MONO}" font-size="30" font-weight="bold" fill="{EMERALD}">{val}</text>')
        p.append(f'<text x="{x}" y="112" font-family="{MONO}" font-size="11" fill="{ZINC400}">{label}</text>')
        x += 168
    # language bar
    p.append(f'<text x="48" y="152" font-family="{MONO}" font-size="11" fill="{ZINC400}">most used languages</text>')
    bx, bw, by = 48, W - 96, 162
    off = 0.0
    for name, n in top:
        seg = bw * n / tot_l
        p.append(f'<rect x="{bx+off:.1f}" y="{by}" width="{max(0,seg-2):.1f}" height="12" rx="2" '
                 f'fill="{LANG_COLORS.get(name, ZINC400)}"/>')
        off += seg
    lx = 48
    for name, n in top:
        p.append(f'<rect x="{lx}" y="{by+28}" width="8" height="8" rx="2" fill="{LANG_COLORS.get(name, ZINC400)}"/>')
        pct = f"{100*n/tot_l:.0f}%"
        p.append(f'<text x="{lx+14}" y="{by+36}" font-family="{MONO}" font-size="11" fill="{ZINC400}">'
                 f'{esc(name)} <tspan fill="{ZINC500}">{pct}</tspan></text>')
        lx += 22 + 9 * (len(name) + 4)
    p.append(f'<text x="{W-48}" y="{H-20}" text-anchor="end" font-family="{MONO}" font-size="10" '
             f'fill="{ZINC500}">updated {date.today().isoformat()}</text>')
    return frame(W, H, p)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    days = contributions(USER)
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", token)
             if not r["fork"]]
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "activity.svg"), "w").write(activity_card(days))
    open(os.path.join(OUT, "stats.svg"), "w").write(stats_card(days, repos, USER))
    print(f"wrote activity.svg and stats.svg ({sum(c for _, c in days)} contributions, {len(repos)} repos)")


if __name__ == "__main__":
    sys.exit(main())
