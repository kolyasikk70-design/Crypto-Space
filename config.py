import os
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")

# LLM Provider Configuration
LLM_API_KEY: str = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
LLM_MODEL: str = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

FREE_MODELS: list = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.1-8b-instruct:free"
]

# Quality Control Threshold
QUALITY_SCORE_THRESHOLD: float = 9.0  # Must score >= 9/10 across metrics

# Interval settings (seconds) - ~15 minutes frequency
POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "14400"))

# Database path
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "database.db")

# Referral Links Mapping
REFERRAL_MAP: Dict[str, str] = {
    "Hyperliquid": os.getenv("REF_HYPERLIQUID", "https://app.hyperliquid.xyz/join/CRYPTO"),
    "Bybit": os.getenv("REF_BYBIT", "https://www.bybit.com/register?affiliate_id=CRYPTO"),
    "Binance": os.getenv("REF_BINANCE", "https://accounts.binance.com/register?ref=CRYPTO"),
    "Backpack": os.getenv("REF_BACKPACK", "https://backpack.exchange/refer/CRYPTO"),
    "Base": os.getenv("REF_BASE", "https://base.org"),
    "OKX": os.getenv("REF_OKX", "https://www.okx.com/join/CRYPTO"),
}

# High Priority Official RSS Sources
RSS_SOURCES: List[Dict[str, str]] = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "weight": "high"},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "weight": "high"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "weight": "high"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "weight": "high"},
    {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/", "weight": "high"},
    {"name": "U.Today", "url": "https://u.today/rss", "weight": "medium"},
    {"name": "Bitcoin.com News", "url": "https://news.bitcoin.com/feed/", "weight": "medium"},
    {"name": "BeInCrypto", "url": "https://beincrypto.com/feed/", "weight": "medium"},
    {"name": "Blockworks", "url": "https://blockworks.co/feed", "weight": "medium"},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "weight": "medium"},
]

# Important keywords for high impact filtering
HIGH_IMPACT_KEYWORDS: List[str] = [
    "sec", "etf", "fed", "fomc", "hack", "exploit", "whale", "unlock", "airdrop",
    "mainnet", "funding", "bounty", "listing", "delisting", "regulation", "court",
    "treasury", "liquidation", "bankruptcy", "binance", "coinbase", "tether", "usdt",
    "usdc", "ethereum", "solana", "bitcoin", "layerzero", "eigenlayer", "monad", "berachain"
]

# Top 20 Crypto Influencers & Key Accounts for Twitter Monitoring
TWITTER_INFLUENCERS: List[Dict[str, str]] = [
    {"handle": "VitalikButerin", "name": "Vitalik Buterin", "category": "Founder"},
    {"handle": "cz_binance", "name": "Changpeng Zhao (CZ)", "category": "Founder"},
    {"handle": "brian_armstrong", "name": "Brian Armstrong", "category": "Founder"},
    {"handle": "aeyakovenko", "name": "Anatoly Yakovenko", "category": "Founder"},
    {"handle": "CryptoHayes", "name": "Arthur Hayes", "category": "Strategist"},
    {"handle": "paoloardoino", "name": "Paolo Ardoino", "category": "Executive"},
    {"handle": "el33th4xor", "name": "Emin Gün Sirer", "category": "Founder"},
    {"handle": "StaniKulechov", "name": "Stani Kulechov", "category": "Founder"},
    {"handle": "haydenzadams", "name": "Hayden Adams", "category": "Founder"},
    {"handle": "sandeepnailwal", "name": "Sandeep Nailwal", "category": "Founder"},
    {"handle": "zachxbt", "name": "ZachXBT", "category": "Security"},
    {"handle": "lookonchain", "name": "Lookonchain", "category": "Onchain"},
    {"handle": "PeckShieldAlert", "name": "PeckShield", "category": "Security"},
    {"handle": "whale_alert", "name": "Whale Alert", "category": "Onchain"},
    {"handle": "tier10k", "name": "Tier10k / DB", "category": "News"},
    {"handle": "saylor", "name": "Michael Saylor", "category": "Executive"},
    {"handle": "cobie", "name": "Cobie", "category": "Trader"},
    {"handle": "100trillionUSD", "name": "PlanB", "category": "Analyst"},
    {"handle": "milesdeutscher", "name": "Miles Deutscher", "category": "Analyst"},
    {"handle": "0xMert_", "name": "Mert Mumtaz", "category": "Founder"}
]

