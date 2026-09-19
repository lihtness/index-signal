# index-signal

Emails when the money should move between the S&P 500 (SPY) and the
equal-weight S&P 500 (RSP). Silent otherwise. The rule and its evidence are in
the `signal_check.py` docstring; the backtest lives in the pf repo
(`scripts/index_rotation.py`).

Runs on GitHub Actions on the 2nd–4th of each month. A flip sends one email a
day for those three days. A status email goes out on 2 January so a quiet year
proves the job is alive. A failed run sends GitHub's own failure email.

## Setup

1. Free Tiingo account → API token (tiingo.com → Account → API).
2. Gmail → Google Account → Security → App passwords (needs 2-step
   verification) → create one for "index-signal".
3. Push this repo to GitHub as **private**, then set the secrets:

       gh secret set TIINGO_TOKEN
       gh secret set GMAIL_USER            # you@gmail.com
       gh secret set GMAIL_APP_PASSWORD
       gh secret set MAIL_TO               # optional, defaults to GMAIL_USER

4. Actions → index signal → Run workflow → tick "test email" to confirm
   delivery.

## Local

    TIINGO_TOKEN=... python signal_check.py --dry-run
    python -m unittest test_signal_check
