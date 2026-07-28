import re
from typing import Dict, Any, Tuple
from config import HIGH_IMPACT_KEYWORDS

class FilterVerifier:
    def __init__(self):
        self.high_impact_regex = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in HIGH_IMPACT_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.spam_keywords = [
            "price prediction", "will reach", "could hit $", "top 5 meme tokens",
            "shiba inu to 1 dollar", "technical analysis shows", "bullish pattern",
            "why market is up today", "sponsored", "promoted", "giveaway"
        ]

    def evaluate_news(self, news_item: Dict[str, Any]) -> Tuple[bool, float, str]:
        title = news_item.get("title", "")
        summary = news_item.get("summary", "")
        text = f"{title} {summary}".lower()

        # Mandatory Pure Crypto Relevance Check
        core_crypto_regex = re.compile(
            r'\b(?:bitcoin|btc|ethereum|eth|solana|sol|crypto|defi|whale|sec|etf|binance|bybit|okx|airdrop|token|altcoin|usdt|usdc|vitalik|saylor|cz|hack|exploit|on-chain|onchain|layer2|l2|arbitrum|optimism|base|monad|hyperliquid|peckshield|lookonchain|tether|ripple|xrp|fed|fomc|mvrv|liquidation|blockchain)\b',
            re.IGNORECASE
        )
        if not core_crypto_regex.search(text):
            return False, 0.0, "Filtered out: Not directly related to core crypto topics"

        # Check for spam or low value price prediction
        for spam_term in self.spam_keywords:
            if spam_term in text:
                return False, 0.0, f"Filtered out: low-value topic ({spam_term})"

        # Base confidence calculation
        matches = self.high_impact_regex.findall(text)
        confidence = 0.50  # Base confidence

        if matches:
            confidence += 0.30

        # Prioritize Twitter influencer posts
        if "twitter" in news_item.get("source_name", "").lower():
            confidence += 0.25

        # Check title indicators (numbers, dollar amounts, official names)
        if re.search(r'\$\d+|\d+\s*million|\d+\s*billion|\bsec\b|\betf\b|\bhack\b|\bexploit\b|\bairdrop\b', text):
            confidence += 0.15

        is_passed = confidence >= 0.85

        category = "General Crypto"
        if "etf" in text or "sec" in text or "fomc" in text or "fed" in text:
            category = "Macro & Regulation"
        elif "hack" in text or "exploit" in text or "bounty" in text:
            category = "Security Alert"
        elif "whale" in text or "liquidation" in text or "treasury" in text:
            category = "On-Chain & Whales"
        elif "unlock" in text or "airdrop" in text or "funding" in text:
            category = "Tokenomics & VC"
        elif "mainnet" in text or "protocol" in text or "layerzero" in text or "monad" in text:
            category = "Infrastructure"

        reason = f"High confidence ({confidence:.2f}) in category [{category}]" if is_passed else "Low impact news item"
        return is_passed, min(confidence, 1.0), category
