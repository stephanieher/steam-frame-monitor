"""Create one assigned issue per distinct listing, including across closed alerts."""
import hashlib
import json
import os
from pathlib import Path

import requests


def notify(status, session, repository, assignee):
    if not status.get("found"):
        print("No listing detected; no issue needed.")
        return
    base = f"https://api.github.com/repos/{repository}/issues"
    issues = []
    page = 1
    while True:
        response = session.get(base, params={"state": "all", "per_page": 100, "page": page}, timeout=30)
        response.raise_for_status()
        batch = response.json()
        issues.extend(issue for issue in batch if "pull_request" not in issue)
        if len(batch) < 100:
            break
        page += 1
    for url in sorted(set(status["matches"])):
        marker = "<!-- steam-frame:" + hashlib.sha256(url.encode()).hexdigest() + " -->"
        if any(marker in (issue.get("body") or "") for issue in issues):
            print(f"Already alerted: {url}")
            continue
        response = session.post(base, json={
            "title": "🚨 Steam Frame found at Elgiganten Sweden",
            "assignees": [assignee],
            "body": f"{marker}\nThe monitor detected a Steam Frame-related product listing on Elgiganten Sweden.\n\n{url}\n\nChecked: {status['checked_at']}\n\nThis does not confirm stock. Check Boka & Hämta availability for Östersund before travelling.",
        }, timeout=30)
        response.raise_for_status()
        issue = response.json()
        if assignee.lower() not in {a["login"].lower() for a in issue.get("assignees", [])}:
            raise RuntimeError(f"Issue created but assignment to {assignee} failed: {issue['html_url']}")
        print(f"Assigned alert created: {issue['html_url']}")


if __name__ == "__main__":
    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                                "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        notify(json.loads(Path("docs/status.json").read_text()), session,
               os.environ["GITHUB_REPOSITORY"], os.environ["ALERT_ASSIGNEE"])
