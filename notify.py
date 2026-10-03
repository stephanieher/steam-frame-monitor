"""Create one assigned availability alert, including across closed alerts."""
import hashlib
import json
import os
from pathlib import Path

import requests


def notify(status, session, repository, assignee):
    if not status.get("found"):
        print("No purchasable Steam Frame detected; no email alert needed.")
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
    availability_marker = "<!-- steam-frame-available-v1 -->"
    if any(availability_marker in (issue.get("body") or "") for issue in issues):
        print("Availability email already requested; no repeat alert.")
        return
    for url in sorted(set(status["matches"])):
        marker = "<!-- steam-frame:" + hashlib.sha256(url.encode()).hexdigest() + " -->"
        if any(marker in (issue.get("body") or "") for issue in issues):
            print(f"Already alerted: {url}")
            continue
        title = "Steam Frame is available to order at Elgiganten Sweden"
        message = "Elgiganten Sweden reports a priced Steam Frame offer as in stock or open for ordering/preorder."
        if status.get("mode") == "official-announcements":
            preorder = status["announcements"][url]["kind"] == "preorder"
            label = "PREORDERS ARE OPEN" if preorder else "AVAILABLE TO BUY"
            title = f"Steam Frame — {label} at Elgiganten Sweden"
            message = (f"# 🟢 STEAM FRAME\n## {label}\n\n"
                       "Elgiganten Sweden has published an official availability announcement.\n\n"
                       f"### [Read Elgiganten's announcement]({url})\n\n"
                       "Follow its shop link to check the current price and delivery date.")
        response = session.post(base, json={
            "title": title,
            "assignees": [assignee],
            "body": f"{availability_marker}\n{marker}\n{message}\n\n{url}\n\nChecked: {status['checked_at']}\n\nÖstersund pickup has not been confirmed; check Boka & Hämta before travelling.",
        }, timeout=30)
        response.raise_for_status()
        issue = response.json()
        if assignee.lower() not in {a["login"].lower() for a in issue.get("assignees", [])}:
            raise RuntimeError(f"Issue created but assignment to {assignee} failed: {issue['html_url']}")
        print(f"Assigned alert created: {issue['html_url']}")
        return


if __name__ == "__main__":
    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                                "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        notify(json.loads(Path("docs/status.json").read_text()), session,
               os.environ["GITHUB_REPOSITORY"], os.environ["ALERT_ASSIGNEE"])
