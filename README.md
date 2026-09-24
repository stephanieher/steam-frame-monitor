# Steam Frame → Elgiganten Sweden Monitor

Checks Elgiganten Sweden's official product sitemap every 30 minutes, at minute 17 and 47 of each hour (UTC). GitHub schedules can be delayed or dropped during heavy load; this is not a guaranteed exact-time service. Manual runs are available under **Actions → Check Elgiganten for Steam Frame → Run workflow**.

## Alerts

A matching Swedish `/product/` URL containing `steam-frame` (including space, underscore or joined variants) creates a GitHub issue assigned to **stephanieher**. Each distinct product URL creates one alert, even if its earlier issue is closed. Enable GitHub issue-assignment notifications on your phone to receive alerts.

A listing does **not** confirm stock, preorder availability, or Östersund Boka & Hämta availability. Product URLs without the Steam Frame name, and pages not yet included in the sitemap, cannot be detected by this monitor.

## Reliability and evidence

- Source: https://www.elgiganten.se/sitemaps/OCSEELG.pdp.index.sitemap.xml (published in Elgiganten Sweden's robots.txt).
- Retries transient HTTP errors, validates XML and Swedish product URLs, supports compressed and nested sitemaps, and limits concurrency to four requests.
- Empty, blocked, malformed or partially failed checks fail the workflow instead of claiming the item is absent. Any confirmed matches still trigger alerts during a partial check.
- Workflow runs are serialized to prevent overlapping alerts and status commits.
- Every run records its timestamp, sitemap count, product count, matches and errors in the Actions summary and a seven-day artifact.
- `docs/status.json` is committed only on the first check or a meaningful result/health change. Its timestamp is the last saved result, not necessarily the latest run. The included HTML viewer is not automatically published as a website.
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
