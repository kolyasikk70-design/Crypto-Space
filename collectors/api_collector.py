import httpx
import asyncio
from typing import List, Dict, Any
from database import Database

class APICollector:
    """
    Collector for crypto data APIs (DefiLlama, CoinGecko, Whale Alert, Token Unlocks, etc.)
    """
    def __init__(self, db: Database):
        self.db = db

    async def fetch_coingecko_prices(self) -> List[Dict[str, Any]]:
        """Fetch live market prices (disabled as news events to avoid raw price dumps)"""
        return []

    async def fetch_defillama_protocols(self) -> List[Dict[str, Any]]:
        """Fetch top TVL changes or major DeFi yield / protocol updates"""
        url = "https://api.llama.fi/protocols"
        new_events = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for p in data[:100]:
                        name = p.get("name")
                        tvl = p.get("tvl", 0)
                        change_1d = p.get("change_1d")
                        if tvl and tvl > 500_000_000 and change_1d and abs(change_1d) >= 15.0:
                            title = f"DefiLlama Alert: {name} TVL {'вырос' if change_1d > 0 else 'упал'} на {change_1d:.1f}% за 24ч (Текущий TVL: ${tvl:,.0f})"
                            source_url = f"https://defillama.com/protocol/{p.get('slug', name.lower())}"
                            if not self.db.is_news_seen(source_url, title):
                                self.db.add_raw_news(
                                    source_name="DefiLlama",
                                    source_url=source_url,
                                    title=title,
                                    summary=f"Значительное изменение TVL протокола {name}: {change_1d}% за сутки. Общая заблокированная стоимость: ${tvl:,.0f}."
                                )
                                new_events.append({
                                    "source_name": "DefiLlama",
                                    "source_url": source_url,
                                    "title": title,
                                    "summary": f"TVL {name} изменился на {change_1d:.1f}% до ${tvl:,.0f}"
                                })
        except Exception as e:
            print(f"[APICollector] Error fetching DefiLlama: {e}")
        return new_events

    async def fetch_all(self) -> List[Dict[str, Any]]:
        results = []
        prices = await self.fetch_coingecko_prices()
        results.extend(prices)
        defillama_events = await self.fetch_defillama_protocols()
        results.extend(defillama_events)
        return results
