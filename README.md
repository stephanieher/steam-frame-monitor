# Steam Frame → Elgiganten Sweden Monitor

**Current limitation:** Elgiganten blocks the hosted GitHub checker. Failure emails have been disabled in account notification settings, but an always-on availability email cannot be promised until hosted access is resolved.

Checks Elgiganten Sweden's official product sitemap every 30 minutes, at minute 17 and 47 of each hour (UTC). GitHub schedules can be delayed or dropped during heavy load; this is not a guaranteed exact-time service. Manual runs are available under **Actions → Check Elgiganten for Steam Frame → Run workflow**.

## Alerts

A matching Swedish Steam Frame product page must report a priced consumer offer in SEK as in stock, available online, or open for preorder before an alert is created. A single GitHub issue assigned to **stephanieher** requests an email to the account’s configured notification address. Closing it or finding another model does not send repeated alerts. No issue is created for an absent listing, an out-of-stock product, or an unknown availability result.

To avoid routine failure emails, turn off Email under GitHub notification settings → System → Actions. Keep Email enabled under Participating, @mentions and custom for availability alerts. Failures remain visible in GitHub Actions.

An alert reflects the consumer availability published in Elgiganten’s product data, including preorders; verify delivery when ordering. Östersund Boka & Hämta availability is not checked. Product URLs without the Steam Frame name, and pages not yet included in the sitemap, cannot be detected by this monitor.

## Reliability and evidence

- Source: https://www.elgiganten.se/sitemaps/OCSEELG.pdp.index.sitemap.xml (published in Elgiganten Sweden's robots.txt).
- Uses browser-compatible TLS/HTTP requests for the public sitemap (plain requests received HTTP 429), retries transient HTTP errors, validates XML and Swedish product URLs, supports compressed and nested sitemaps, and limits concurrency to four requests.
- Empty, blocked, malformed or partially failed checks, including unknown product availability, fail the workflow instead of claiming the item is absent. Confirmed purchasable products can still trigger an alert during a partial check.
- Hosted access is currently blocked: both Ubuntu and macOS GitHub runners received HTTP 429. A successful local check does not establish a working hosted monitor. The cloud availability alert remains unverified until a hosted checker can reach Elgiganten.
- Workflow runs are serialized to prevent overlapping alerts and status commits.
- Every run records its timestamp, sitemap count, product count, matches and errors in the Actions summary and a seven-day artifact.
- `docs/status.json` is committed on the first check, a meaningful result/health change, or once per UTC calendar month to keep repository activity current. Its timestamp is the last saved result, not necessarily the latest run. The included HTML viewer is not automatically published as a website.
- Workflow permissions are limited to repository contents and issues. No personal access token or external service is required.
- Standard GitHub-hosted runners are free for this public repository. GitHub may disable scheduled workflows after 60 days without repository activity; periodically check that the schedule remains enabled.

## Local development

Use Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python monitor.py
```

`notify.py` is invoked by the workflow with `GH_TOKEN`, `GITHUB_REPOSITORY` and `ALERT_ASSIGNEE`. Tests use mocked GitHub responses and never create test issues.

## References

- https://www.elgiganten.se/robots.txt
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
