#!/usr/bin/env python3
"""Check Elgiganten Sweden's official product sitemaps without hiding failures."""
import concurrent.futures
import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SITEMAP_INDEX = "https://www.elgiganten.se/sitemaps/OCSEELG.pdp.index.sitemap.xml"
STATUS_FILE = Path("docs/status.json")
USER_AGENT = "SteamFrameAvailabilityMonitor/1.1 (+https://github.com/stephanieher/steam-frame-monitor)"


def swedish_url(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc in {"www.elgiganten.se", "elgiganten.se"}


def is_steam_frame_url(url):
    if not swedish_url(url):
        return False
    path = unquote(urlparse(url).path).lower()
    return path.startswith("/product/") and bool(re.search(r"(?<![a-z])steam[-_\s]*frame(?![a-z])", path))


def get(url):
    if not swedish_url(url):
        raise ValueError(f"Unexpected sitemap host: {url}")
    # Each worker gets its own session; never share mutable sessions across threads.
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"], respect_retry_after_header=False)
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml"},
                               timeout=(10, 35))
        response.raise_for_status()
        if not swedish_url(response.url):
            raise ValueError("Sitemap redirected outside Elgiganten Sweden")
        return response


def parse_sitemap(data):
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    root = ET.fromstring(data)
    kind = root.tag.rsplit("}", 1)[-1]
    if kind not in {"sitemapindex", "urlset"}:
        raise ValueError(f"Expected a sitemap, received {kind}")
    entry_tag = "sitemap" if kind == "sitemapindex" else "url"
    urls = []
    for entry in root:
        if entry.tag.rsplit("}", 1)[-1] != entry_tag:
            continue
        for child in entry:
            if child.tag.rsplit("}", 1)[-1] == "loc" and child.text:
                urls.append(child.text.strip())
    if not urls:
        raise ValueError("Sitemap contains no URLs")
    if any(not swedish_url(url) for url in urls):
        raise ValueError("Sitemap contains a URL outside Elgiganten Sweden")
    return kind, sorted(set(urls))


def inspect_sitemap(url):
    return parse_sitemap(get(url).content)


def check():
    pending = {SITEMAP_INDEX}
    visited, products, matches, errors = set(), set(), set(), []
    successful = 0
    # Allow nested indexes, but bound unexpected cycles or runaway changes.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch = pending - visited
            if not batch:
                break
            if len(visited) + len(batch) > 200:
                errors.append("Sitemap limit exceeded (200)")
                break
            visited.update(batch)
            futures = {pool.submit(inspect_sitemap, url): url for url in batch}
            pending = set()
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    kind, urls = future.result()
                    successful += 1
                    if kind == "sitemapindex":
                        pending.update(urls)
                    else:
                        product_urls = {u for u in urls if urlparse(u).path.startswith("/product/")}
                        if not product_urls:
                            raise ValueError("Product sitemap contains no product URLs")
                        products.update(product_urls)
                        matches.update(u for u in product_urls if is_steam_frame_url(u))
                except Exception as exc:
                    errors.append(f"{url}: {type(exc).__name__}: {exc}")
    if not products and not errors:
        errors.append("No products checked; sitemap index may be cyclic or invalid")
    return {
        "found": bool(matches),
        "complete": not errors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": SITEMAP_INDEX,
        "matches": sorted(matches),
        "sitemaps_checked": successful,
        "sitemaps_attempted": len(visited),
        "products_checked": len(products),
        "partial_errors": sorted(errors),
        "error": f"Incomplete check: {len(errors)} sitemap error(s)" if errors else None,
    }


def main():
    status = check()
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0 if status["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
