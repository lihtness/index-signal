"""Which S&P index should the money be in: cap-weight (SPY) or equal-weight (RSP)?

The rule, tested on 1990-2026 in pf's scripts/index_rotation.py:

    gap      RSP's trailing twelve-month total return minus SPY's, read at
             each month-end close
    state    equal-weight once the gap goes above +1 point, cap-weight once it
             goes below -1 point, unchanged in between

The band halved the flips of the bare sign rule (36 -> 16 over 36 years) and
cost no return. State is replayed from the whole history on every run, so
nothing is stored: a run on the 2nd, 3rd and 4th of a month reaches the same
answer each time, and a flip sends three emails and then goes quiet.

    python signal_check.py            # check, email on a flip
    python signal_check.py --dry-run  # print the reading and any email, send nothing
    python signal_check.py --test-email

Environment: TIINGO_TOKEN, GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO (optional,
defaults to GMAIL_USER).
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
import urllib.request
from datetime import date, datetime, timezone
from email.message import EmailMessage

CAP, EQUAL = "SPY", "RSP"
BAND = 0.01
SINCE = "2003-05-01"          # RSP's first month


def fetch(ticker: str) -> list[tuple[str, float]]:
    """Daily (date, adjusted close), oldest first."""
    url = (f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
           f"?startDate={SINCE}&token={os.environ['TIINGO_TOKEN']}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        rows = json.load(resp)
    if not rows:
        raise RuntimeError(f"Tiingo returned no prices for {ticker}")
    return [(r["date"][:10], float(r["adjClose"])) for r in rows]


def month_ends(daily: list[tuple[str, float]], today: date) -> dict[str, float]:
    """Last close of each completed month, keyed 'YYYY-MM'. The current month
    is not finished, so it is left out."""
    out: dict[str, float] = {}
    for d, close in daily:
        out[d[:7]] = close
    out.pop(today.strftime("%Y-%m"), None)
    return out


def states(cap: dict[str, float], equal: dict[str, float]) -> list[tuple[str, float, bool]]:
    """(month, gap, equal_weight?) for every month with twelve months behind it."""
    ms = sorted(set(cap) & set(equal))
    out: list[tuple[str, float, bool]] = []
    st: bool | None = None
    for i in range(12, len(ms)):
        m, p = ms[i], ms[i - 12]
        gap = (equal[m] / equal[p]) - (cap[m] / cap[p])
        if st is None:
            st = gap > 0
        elif st and gap < -BAND:
            st = False
        elif not st and gap > BAND:
            st = True
        out.append((m, gap, st))
    return out


def name(eq: bool) -> str:
    return f"equal-weight ({EQUAL})" if eq else f"cap-weight S&P 500 ({CAP})"


def flip_email(prev: tuple[str, float, bool], now: tuple[str, float, bool]) -> tuple[str, str]:
    m, gap, eq = now
    new, old = (EQUAL, CAP) if eq else (CAP, EQUAL)
    subject = f"Index signal flipped to {name(eq)}"
    body = f"""At the {m} month-end close, {EQUAL} has returned {gap:+.1%} against {CAP}
over the last twelve months (it was {prev[1]:+.1%} a month earlier). The signal
moves past a 1-point band, so it has flipped from {name(prev[2])} to {name(eq)}.

  IRA / tax-advantaged:  sell {old}, buy {new} with the whole balance.
  Taxable:               send new contributions to {new}. Sell nothing.

This email is sent on three consecutive days, then stops until the next flip.
"""
    return subject, body


def status_email(now: tuple[str, float, bool], hist: list[tuple[str, float, bool]]) -> tuple[str, str]:
    m, gap, eq = now
    flips = [b for a, b in zip(hist, hist[1:]) if a[2] != b[2]]
    last = flips[-1][0] if flips else "never"
    subject = f"Index signal: still {name(eq)} (yearly check-in)"
    body = f"""The job is running. At the {m} close {EQUAL} is {gap:+.1%} against {CAP}
over twelve months; the signal is {name(eq)}, unchanged since {last}.
Nothing to do.
"""
    return subject, body


def send(subject: str, body: str) -> None:
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    msg = EmailMessage()
    msg["From"], msg["To"] = user, os.environ.get("MAIL_TO") or user
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-email", action="store_true")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date()
    hist = states(month_ends(fetch(CAP), today), month_ends(fetch(EQUAL), today))
    prev, now = hist[-2], hist[-1]
    print(f"{now[0]}: gap {now[1]:+.2%} -> {name(now[2])}"
          f"{'  (FLIPPED)' if prev[2] != now[2] else ''}")

    mail = None
    if prev[2] != now[2]:
        mail = flip_email(prev, now)
    elif args.test_email or (today.month == 1 and today.day == 2):
        mail = status_email(now, hist)

    if mail and args.dry_run:
        print(f"\n--- would send ---\nSubject: {mail[0]}\n\n{mail[1]}")
    elif mail:
        send(*mail)
        print(f"sent: {mail[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
