"""Watch Elgiganten Sweden's public press-release RSS, without an account.

Conservative: only explicit present availability in the RSS headline/summary
qualifies. This does not check store inventory or every social-media post.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

SOURCE = 'https://via.tt.se/rss/releases/latest?publisherId=3236639'
STARTED = datetime(2026, 10, 3, tzinfo=timezone.utc)
NAME = r'\bsteam\s+frame\b'
# Require the product to be the subject of an explicit present-tense statement.
PATTERNS = {
    'preorder': [
        NAME + r'\s+(?:kan\s+)?(?:nu\s+)?förbeställas\s+(?:nu\s+)?(?:hos|på)\s+elgiganten\b',
        NAME + r'\s+(?:is\s+)?(?:now\s+)?available\s+(?:now\s+)?(?:to\s+preorder|for\s+pre[- ]?order)\s+(?:at|from)\s+elgiganten\b',
        r'\bförbeställ\s+(?:nu\s+)?' + NAME + r'\s+(?:nu\s+)?(?:hos|på)\s+elgiganten\b',
    ],
    'available': [
        NAME + r'\s+finns\s+(?:nu\s+)?(?:att\s+köpa|i\s+lager)\s+(?:nu\s+)?(?:hos|på)\s+elgiganten\b',
        NAME + r'\s+(?:kan\s+)?(?:nu\s+)?köpas\s+(?:nu\s+)?(?:hos|på)\s+elgiganten\b',
        NAME + r'\s+is\s+(?:now\s+)?(?:in\s+stock|available\s+to\s+buy)\s+(?:now\s+)?(?:at|from)\s+elgiganten\b',
    ],
}
NEGATIVE = re.compile(r'\b(?:inte|ej|slutsåld\w*|slut\s+i\s+lager|kommer|snart|imorgon|i\s+morgon|från\s+och\s+med|not|no\s+longer|sold\s+out|out\s+of\s+stock|soon|tomorrow|will|would|if|om|rykte\w*|rumou?r\w*|exempel|example)\b', re.I)


def announcement_kind(text):
    text = re.sub(r'<[^>]+>', ' ', html.unescape(text))
    text = re.sub(r'\s+', ' ', text).strip().lower()
    # A contradictory/future statement anywhere in the summary fails closed.
    if NEGATIVE.search(text):
        return None
    for kind, patterns in PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return kind
    return None


def parse_feed(data, now):
    root = ET.fromstring(data)
    channel = root.find('channel')
    if channel is None or channel.findtext('title') != 'Elgiganten - senaste pressmeddelandena':
        raise ValueError('Unexpected publisher feed')
    items = channel.findall('item')
    if not items:
        raise ValueError('Empty announcement feed; access is unverified')
    matches, details = [], {}
    for item in items:
        url = item.findtext('link', '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != 'via.tt.se' or not parsed.path.startswith('/pressmeddelande/'):
            raise ValueError('Unexpected announcement URL')
        published = parsedate_to_datetime(item.findtext('pubDate', ''))
        if published.tzinfo is None:
            raise ValueError('Announcement date missing timezone')
        if not max(STARTED, now - timedelta(days=7)) <= published <= now:
            continue
        title = item.findtext('title', '')
        description = item.findtext('description', '')
        kind = announcement_kind(title + '. ' + description)
        if kind:
            matches.append(url)
            details[url] = {'kind': kind, 'title': title, 'published_at': published.isoformat()}
    return items, sorted(set(matches)), details


def check(session=requests, now=None):
    now = now or datetime.now(timezone.utc)
    status = {'checked_at': now.isoformat(), 'source': SOURCE,
              'mode': 'official-announcements', 'complete': False, 'found': False,
              'matches': [], 'announcements': {}, 'announcement_count': 0,
              'error': None, 'partial_errors': []}
    try:
        response = session.get(SOURCE, timeout=45)
        response.raise_for_status()
        items, matches, details = parse_feed(response.content, now)
        status.update(complete=True, found=bool(matches), matches=matches,
                      announcements=details, announcement_count=len(items))
    except Exception as exc:
        status['error'] = str(exc)
    return status


if __name__ == '__main__':
    status = check()
    Path('docs').mkdir(exist_ok=True)
    Path('docs/status.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(status, indent=2, ensure_ascii=False))
    sys.exit(0 if status['complete'] else 1)
