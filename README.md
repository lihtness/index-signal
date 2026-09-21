# index-signal

Equal-weight vs cap-weight S&P 500: a measurement, published.

The same five hundred companies can be held two ways — weighted by company
size, which is what SPY does, or weighted equally, which is what RSP does. This
repo tracks the gap between them on twelve-month total return, replays a
published rule built on that gap, and renders both as a page.

**It describes. It does not advise.** The page reports the reading, the full
history, and what the rule did in the decades it helped and the decades it
cost. No position is suggested anywhere in it.

## What the evidence says

The rule's parameters were fitted on 1990–2026. Run on 1927–1989, which nothing
was fitted to, it finished **within a rounding error of holding cap-weight
alone**: ahead in **44% of rolling ten-year windows**, median **−1.4%**. It adds
where the largest companies lag (1930s +1.2 pts/yr, 1940s +1.0, 2000s +1.6) and
gives it back where they lead (1950s −0.7, 2020s −1.4). Through 1929–1932 both
fell 84% — nothing here shortens a crash.

So it is insurance with an expected return near zero, not an edge, and the page
says so in those words. The backtest is in the `pf` repo
(`scripts/index_rotation.py`, `scripts/index_rotation_1926.py`).

## What runs here

| workflow | when | what it does |
|---|---|---|
| `index signal` | 2nd–4th monthly | emails the author on a state change; silent otherwise |
| `status page`  | daily | rebuilds the public page and deploys it to GitHub Pages |

The page is static and self-contained — the chart is server-rendered SVG, so it
reads with JavaScript off, and there is no server anywhere in this. State is
replayed from the whole price history on every build, so nothing is stored and
any build is reproducible from the data alone.

## Local

    TIINGO_TOKEN=... python signal_check.py --dry-run
    TIINGO_TOKEN=... python status.py --out site/index.html
    python -m unittest test_signal_check

## Setup

1. Free Tiingo account → API token (tiingo.com → Account → API).
2. Gmail → Google Account → Security → App passwords (needs 2-step
   verification) → create one for "index-signal".
3. Secrets:

       gh secret set TIINGO_TOKEN
       gh secret set GMAIL_USER            # you@gmail.com
       gh secret set GMAIL_APP_PASSWORD
       gh secret set MAIL_TO               # optional, defaults to GMAIL_USER

4. Settings → Pages → Source: **GitHub Actions**.

## Disclaimer

Published research, not investment advice. The author is not an investment
adviser. Nothing here is a recommendation to buy, sell or hold any security.
Past measurements do not predict future results.
