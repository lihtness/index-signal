"""The flip email's view model. The markup lives in templates/flip.html.j2.

Mail clients are a decade behind the web, so the template is tables and inline
styles only — no flexbox, grid, SVG or external images, since Gmail drops all
four. The chart is table cells with background colours, which every client
since 2004 renders, and this module works out their widths so the template
stays declarative.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

Reading = tuple[str, float, bool]        # month, 12m gap, equal-weight?

HALF = 150                               # px either side of the chart's centre
CHART_MONTHS = 36

env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["pct"] = lambda x, dp=1: f"{x:+.{dp}%}"


def pretty(m: str) -> str:
    y, mo = m.split("-")
    return f"{date(int(y), int(mo), 1):%b %Y}"


def run_length(hist: list[Reading]) -> tuple[int, str]:
    """How many months the current state has held, and the month it began."""
    n = 1
    for a, b in zip(reversed(hist[:-1]), reversed(hist[1:])):
        if a[2] != b[2]:
            return n, b[0]
        n += 1
    return n, hist[0][0]


def flips(hist: list[Reading]) -> list[Reading]:
    return [b for a, b in zip(hist, hist[1:]) if a[2] != b[2]]


def chart_rows(hist: list[Reading], months: int = CHART_MONTHS, half: int = HALF) -> list[dict]:
    """One row a month: a bar of `width` px on one side of a centre line, and
    a label every sixth month counting back from the newest."""
    rows = hist[-months:]
    scale = max(0.02, max(abs(g) for _, g, _ in rows))
    out = []
    for i, (m, gap, _) in enumerate(rows):
        w = max(2, round(abs(gap) / scale * half))
        out.append({
            "label": pretty(m) if (len(rows) - 1 - i) % 6 == 0 else "",
            "gap": gap,
            "ahead": gap > 0,
            "width": w,
            "pad": half - w,
            "half": half,
        })
    return out


def flip_html(prev: Reading, now: Reading, hist: list[Reading],
              cap: str, equal: str, band: float, page: str = "") -> str:
    m, gap, eq = now
    held, began = run_length(hist[:-1])
    return env.get_template("flip.html.j2").render(
        cap=cap, equal=equal, band=band, page=page,
        month=pretty(m), gap=gap, equal_ahead=eq,
        buy=equal if eq else cap, sell=cap if eq else equal,
        held=held, began=pretty(began),
        was="equal-weight" if hist[-2][2] else "cap-weight",
        chart=chart_rows(hist),
        flips=[{"month": pretty(f[0]), "gap": f[1],
                "to": f"equal-weight {equal}" if f[2] else f"cap-weight {cap}"}
               for f in reversed(flips(hist)[-6:-1])],
    )
