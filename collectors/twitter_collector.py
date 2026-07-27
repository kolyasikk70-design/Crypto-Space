import asyncio
import json
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from config import TWITTER_INFLUENCERS
from database import Database

class TwitterCollector:
    """
    Collector for Twitter (X) crypto influencer posts using syndication and RSS fallbacks.
    """
    def __init__(self, db: Database):
        self.db = db
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    async def fetch_user_tweets(self, client: httpx.AsyncClient, account: Dict[str, str]) -> List[Dict[str, Any]]:
        handle = account["handle"]
        name = account["name"]
        category = account.get("category", "Influencer")
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
        
        new_items = []
        try:
            resp = await client.get(url, headers=self.headers, timeout=12.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                script = soup.find("script", id="__NEXT_DATA__")
                if script and script.string:
                    data = json.loads(script.string)
                    entries = data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
                    
                    for entry in entries:
                        tweet = entry.get("content", {}).get("tweet", {})
                        if not tweet:
                            continue

                        tweet_id = tweet.get("id_str")
                        text = tweet.get("text", "").strip()
                        user_info = tweet.get("user", {})
                        screen_name = user_info.get("screen_name", handle)

                        if not text or not tweet_id:
                            continue

                        # Ignore trivial short replies (under 25 chars) unless breaking news account
                        if text.startswith("@") and len(text) < 25 and category != "News":
                            continue

                        tweet_url = f"https://x.com/{screen_name}/status/{tweet_id}"
                        source_title = f"Twitter (@{screen_name}): {text[:80]}..." if len(text) > 80 else f"Twitter (@{screen_name}): {text}"

                        # Extract media image if available
                        image_url = ""
                        entities = tweet.get("entities", {})
                        media_list = entities.get("media", [])
                        if media_list and isinstance(media_list, list):
                            image_url = media_list[0].get("media_url_https", "")

                        # Check DB duplicate
                        if not self.db.is_news_seen(tweet_url, source_title):
                            added = self.db.add_raw_news(
                                source_name=f"Twitter (@{screen_name})",
                                source_url=tweet_url,
                                title=source_title,
                                summary=f"Пост от {name} (@{screen_name}):\n\n{text}",
                                image_url=image_url
                            )
                            if added:
                                new_items.append({
                                    "source_name": f"Twitter (@{screen_name})",
                                    "source_url": tweet_url,
                                    "title": source_title,
                                    "summary": text,
                                    "image_url": image_url,
                                    "author": name,
                                    "handle": screen_name,
                                    "category": category
                                })
        except Exception as e:
            print(f"[TwitterCollector] Error fetching @{handle}: {e}")

        return new_items

    async def fetch_all(self) -> List[Dict[str, Any]]:
        all_new_items = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [self.fetch_user_tweets(client, account) for account in TWITTER_INFLUENCERS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    all_new_items.extend(res)
        return all_new_items
