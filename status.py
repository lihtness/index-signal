"""The public status page: what the signal reads now, and how it has played out.

`signal_check.py` decides whether to send an email. This renders the same
replayed history as a page anyone can open, and it describes rather than
instructs — the reading, the record, and what the rule did in the decades it
helped and the decades it cost. No position is suggested here.

The page is static and self-contained: the chart is server-rendered SVG, so it
reads with JavaScript switched off, and the script only adds the hover
crosshair. Published by GitHub Actions to GitHub Pages; there is no server.

    TIINGO_TOKEN=... python status.py --out site/index.html
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

import signal_check as sc
from render import flips, pretty, run_length

# What the century test found decade by decade, from pf's
# scripts/index_rotation_1926.py: the rule adds where the largest companies lag
# and gives it back where they lead. Points a year against holding cap-weight.
DECADES = [
    {"name": "1930s", "regime": "lagged", "v": +1.2},
    {"name": "1940s", "regime": "lagged", "v": +1.0},
    {"name": "1950s", "regime": "led", "v": -0.7},
    {"name": "2000s", "regime": "lagged", "v": +1.6},
    {"name": "2020s", "regime": "led", "v": -1.4},
]

W, H = 960.0, 370.0
PAD_L, PAD_R, PAD_T, PAD_B = 48.0, 12.0, 16.0, 30.0

env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["pct"] = lambda x, dp=1: f"{x:+.{dp}%}"


def geometry(hist: list[tuple[str, float, bool]]) -> dict:
    """Server-rendered chart geometry: the gap line, the zero line, the band,
    and year ticks. Units are SVG user space, so the page needs no script to
    draw itself."""
    gaps = [g for _, g, _ in hist]
    span = max(0.02, max(abs(g) for g in gaps)) * 1.08
    iw, ih = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    n = len(hist)

    x = lambda i: PAD_L + (iw * i / (n - 1) if n > 1 else 0)
    y = lambda g: PAD_T + ih * (1 - (g + span) / (2 * span))

    pts = [(x(i), y(g)) for i, (_, g, _) in enumerate(hist)]
    line = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    zero = y(0.0)
    area = (line + f" L{pts[-1][0]:.1f},{zero:.1f} L{pts[0][0]:.1f},{zero:.1f} Z")

    ticks = []
    for i, (m, _, _) in enumerate(hist):
        if m.endswith("-01") and int(m[:4]) % 3 == 0:
            ticks.append({"x": round(x(i), 1), "label": m[:4]})

    # Ticks are chosen from the span, not fixed: a quiet decade and a 2009
    # deserve different gridlines, and hardcoding them bunches every label
    # into the middle of a tall chart the moment the range widens.
    step = next(s for s in (0.02, 0.05, 0.10, 0.20, 0.25, 0.50) if span / s <= 4)
    ylabs, v = [], 0.0
    while v <= span:
        for u in ({v, -v} if v else {0.0}):
            ylabs.append({"y": round(y(u), 1),
                          "label": f"{u:+.0%}" if u else "0"})
        v += step

    return {
        "w": W, "h": H, "line": line, "area": area,
        "zero": round(zero, 1),
        "band_top": round(y(sc.BAND), 1), "band_bot": round(y(-sc.BAND), 1),
        "x0": PAD_L, "x1": round(W - PAD_R, 1),
        "ticks": ticks, "ylabs": ylabs,
        "points": [[round(px, 1), round(py, 1)] for px, py in pts],
    }


def live(daily_cap: list[tuple[str, float]],
         daily_eq: list[tuple[str, float]]) -> dict | None:
    """The gap as it stands today, on the latest daily closes.

    The rule reads month-end closes, so between month-ends its state is simply
    the last one. That leaves a page opened mid-month showing a number up to
    thirty days old, which looks stale and is easy to misread as the current
    market. This reports the running gap alongside it, labelled as what it is:
    provisional, and not what the rule acts on.
    """
    def ret(series: list[tuple[str, float]]) -> tuple[str, float] | None:
        if not series:
            return None
        last_d, last_p = series[-1]
        target = date.fromisoformat(last_d) - timedelta(days=365)
        prior = [p for d, p in series if date.fromisoformat(d) <= target]
        return (last_d, last_p / prior[-1] - 1) if prior else None

    a, b = ret(daily_cap), ret(daily_eq)
    if not a or not b:
        return None
    return {"asof": a[0], "gap": b[1] - a[1]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="site/index.html")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date()
    daily_cap, daily_eq = sc.fetch(sc.CAP), sc.fetch(sc.EQUAL)
    cap = sc.month_ends(daily_cap, today)
    equal = sc.month_ends(daily_eq, today)
    hist = sc.states(cap, equal)
    if not hist:
        print("no history — refusing to write a page", file=sys.stderr)
        return 1

    m, gap, eq = hist[-1]
    held, began = run_length(hist)
    fl = flips(hist)

    html = env.get_template("status.html.j2").render(
        cap=sc.CAP, equal=sc.EQUAL, band=sc.BAND,
        month=pretty(m), gap=gap, equal_ahead=eq,
        ahead=sc.EQUAL if gap > 0 else sc.CAP,
        held=held, began=pretty(began),
        since_first=pretty(hist[0][0]),
        months=len(hist),
        chart=geometry(hist),
        series=[[pretty(a), round(b, 4), c] for a, b, c in hist],
        decades=DECADES,
        flips=[{"month": pretty(f[0]), "gap": f[1], "to": sc.EQUAL if f[2] else sc.CAP}
               for f in reversed(fl)],
        n_flips=len(fl),
        table=[{"month": pretty(a), "gap": b, "state": sc.EQUAL if c else sc.CAP}
               for a, b, c in reversed(hist)],
        live=live(daily_cap, daily_eq),
        built=today.isoformat(),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} · {len(hist)} months · {len(fl)} flips · latest {m} {gap:+.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
