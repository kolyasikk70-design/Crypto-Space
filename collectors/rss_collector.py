import asyncio
import html
import httpx
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from config import RSS_SOURCES
from database import Database

class RSSCollector:
    def __init__(self, db: Database):
        self.db = db
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return html.unescape(text).strip()

    def _extract_image_url(self, entry: Any) -> str:
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        if hasattr(entry, 'enclosures') and entry.enclosures:
            return entry.enclosures[0].get('href', '')
        return ''

    async def fetch_feed(self, client: httpx.AsyncClient, source: Dict[str, str]) -> List[Dict[str, Any]]:
        new_items = []
        name = source["name"]
        url = source["url"]

        try:
            response = await client.get(url, headers=self.headers, timeout=15.0)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                for entry in feed.entries:
                    item_title = html.unescape(getattr(entry, "title", "")).strip()
                    item_link = getattr(entry, "link", "").strip()
                    item_summary = self._clean_html(getattr(entry, "summary", getattr(entry, "description", "")))
                    item_image = self._extract_image_url(entry)

                    if not item_title or not item_link:
                        continue

                    # Check DB duplicate
                    if not self.db.is_news_seen(item_link, item_title):
                        added = self.db.add_raw_news(
                            source_name=name,
                            source_url=item_link,
                            title=item_title,
                            summary=item_summary,
                            image_url=item_image
                        )
                        if added:
                            new_items.append({
                                "source_name": name,
                                "source_url": item_link,
                                "title": item_title,
                                "summary": item_summary,
                                "image_url": item_image
                            })
        except Exception as e:
            print(f"[RSSCollector] Error fetching {name} ({url}): {e}")

        return new_items

    async def fetch_all(self) -> List[Dict[str, Any]]:
        all_new_items = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [self.fetch_feed(client, source) for source in RSS_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    all_new_items.extend(res)
        return all_new_items
