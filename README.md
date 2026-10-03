# Steam Frame → Elgiganten Sweden announcement watch

Watches Elgiganten Sweden's **official press-release RSS** on GitHub every 30 minutes. Runs while your Mac is off and needs no new account, login, or paid monitoring service.

## What triggers the email

A recent RSS headline or summary must explicitly say Steam Frame can be bought or preordered at Elgiganten now. The email uses a large green indicator and clear **AVAILABLE TO BUY** or **PREORDERS ARE OPEN** wording with the official announcement link. General mentions, negative or future statements, and releases older than seven days or published before 3 October 2026 do not alert.

The checker creates one issue assigned to `stephanieher`, which requests an email through the existing GitHub notification settings. It checks both open and closed issues and sends no repeat availability alert, even if another model appears. Actual inbox delivery depends on GitHub and mail filtering; no fake availability email is sent for testing.

GitHub Actions email notifications were disabled to stop routine failure emails. Keep **Participating, @mentions and custom → Email** enabled for the availability alert. Other repositories' notifications are separate.

## Scope and limitations

This watches public press announcements, **not live stock or all Facebook posts**. Conservative wording rules can miss an announcement, and information published only in a full article, on Facebook, or on a product page may not appear in the RSS headline/summary. Check the linked shop page for current price, delivery, and Östersund pickup before ordering.

The old product-page checker remains in `monitor.py` for reference but is no longer scheduled: Elgiganten blocked both Ubuntu and macOS GitHub runners. A manual Facebook access experiment also returned a login page from the cloud. Neither source is used by the active watch.

## Operation

- Source: [Elgiganten's official RSS](https://via.tt.se/rss/releases/latest?publisherId=3236639), linked by [its Via TT pressroom](https://via.tt.se/pressrum/3236639/elgiganten) and connected from [Elgiganten's own pressroom](https://www.elgiganten.se/om-elgiganten/pressrum).
- Schedule: minute 17 and 47 each hour. GitHub schedules may be delayed or dropped.
- Manual check: **Actions → Check Elgiganten for Steam Frame → Run workflow**.
- Every run validates the publisher, release links and dates. Blocked, empty or malformed feeds fail visibly in Actions instead of reporting a successful absence.
- The run summary and seven-day artifact contain the result. `docs/status.json` is saved for meaningful health/result changes and monthly; its timestamp is the last saved result, not every check.
- Serialized runs and deduplication prevent repeated alerts. Permissions are limited to repository contents and issues, using GitHub's built-in token.
- GitHub can disable public repository schedules after 60 days without activity. Monthly status commits help keep this repository active.

## Development

Use Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python announcement_monitor.py
```

Tests cover current/preorder claims, negation, unrelated products, dates, invalid sources, access failures, email wording and duplicate suppression without sending test issues.
