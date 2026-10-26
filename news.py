"""Feed newsów: Google News RSS, tylko nagłówki z ostatnich N godzin. Sama biblioteka standardowa."""
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET_XML
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import confload

config = confload.load()

RSS_URL = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def parse_rss(xml_bytes: bytes, since: datetime, limit: int) -> list:
    root = ET_XML.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        pub = item.findtext("pubDate")
        if not title or not pub:
            continue
        try:
            published = parsedate_to_datetime(pub)
        except (TypeError, ValueError):
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= since:
            items.append({"czas_utc": published.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                          "tytul": title})
    items.sort(key=lambda x: x["czas_utc"], reverse=True)
    return items[:limit]


def fetch_headlines(query: str, now_utc: datetime) -> list:
    url = RSS_URL.format(q=urllib.parse.quote(f"{query} when:1d"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (od-0-do-milionera)"})
    body, last = None, None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            break
        except Exception as e:       # 13.10.2026: HTTP 503 z Google News, jedna próba = stracony dzień
            last = e
            time.sleep(20 * (attempt + 1))
    if body is None:
        raise last
    since = now_utc - timedelta(hours=config.NEWS_HOURS)
    return parse_rss(body, since, config.MAX_HEADLINES)
