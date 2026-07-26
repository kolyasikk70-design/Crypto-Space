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
        """Fetch live market prices and 24h changes for top coins"""
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,cardano,dogecoin&vs_currencies=usd&include_24hr_change=true"
        events = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    btc = data.get("bitcoin", {})
                    eth = data.get("ethereum", {})
                    sol = data.get("solana", {})

                    btc_price = btc.get("usd", 0)
                    btc_change = btc.get("usd_24h_change", 0)

                    eth_price = eth.get("usd", 0)
                    eth_change = eth.get("usd_24h_change", 0)

                    sol_price = sol.get("usd", 0)
                    sol_change = sol.get("usd_24h_change", 0)

                    # Create a market snapshot item if there's significant movement or for daily context
                    if btc_price > 0:
                        title = f"Рыночный импульс: BTC ${btc_price:,.0f} ({btc_change:+.1f}%), ETH ${eth_price:,.0f} ({eth_change:+.1f}%), SOL ${sol_price:,.1f} ({sol_change:+.1f}%)"
                        source_url = f"https://www.coingecko.com/en/coins/bitcoin#{btc_price}"
                        summary = f"Текущие реальные котировки рынка: Биткоин торгуется по ${btc_price:,.2f} ({btc_change:+.2f}% за 24ч), Ethereum ${eth_price:,.2f} ({eth_change:+.2f}%), Solana ${sol_price:,.2f} ({sol_change:+.2f}%)."
                        
                        events.append({
                            "source_name": "CoinGecko API",
                            "source_url": source_url,
                            "title": title,
                            "summary": summary
                        })
        except Exception as e:
            print(f"[APICollector] Error fetching CoinGecko prices: {e}")
        return events

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
