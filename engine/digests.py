import time
from typing import List, Dict, Any
from database import Database

class DigestGenerator:
    def __init__(self, db: Database):
        self.db = db

    def generate_morning_digest(self) -> Dict[str, Any]:
        recent_posts = self.db.get_recent_posts(limit=10)
        bullets = []
        for p in recent_posts[:5]:
            title = p.get("title", "").replace("🚨 ", "").replace("🔥 ", "")
            bullets.append(f"• **{title}**")

        content_lines = [
            "🌅 **УТРЕННИЙ КРИПТО-ДАЙДЖЕСТ | CRYPTO EDITOR**\n",
            "Главные события и главные сдвиги рынка за прошедшую ночь:\n",
            "\n".join(bullets) if bullets else "• Рынок торгуется в узком диапазоне. Крупных аномалий не зафиксировано.",
            "\n💡 **На что обратить внимание сегодня:**",
            "1. Динамика притоков/оттоков в спотовые BTC и ETH ETF.",
            "2. Ончейн-перемещения крупных держателей перед закрытием дневной свечи.\n",
            "📊 *Будьте в курсе самого главного за 60 секунд.*"
        ]

        return {
            "title": "🌅 УТРЕННИЙ КРИПТО-ДАЙДЖЕСТ",
            "content": "\n".join(content_lines),
            "post_type": "digest",
            "category": "Digest"
        }

    def generate_evening_digest(self) -> Dict[str, Any]:
        recent_posts = self.db.get_recent_posts(limit=10)
        bullets = []
        for p in recent_posts[:5]:
            title = p.get("title", "").replace("🚨 ", "").replace("🔥 ", "")
            bullets.append(f"• **{title}**")

        content_lines = [
            "🌙 **ВЕЧЕРНИЙ ИТОГ РЫНКА | CRYPTO EDITOR**\n",
            "Ключевые события дня, изменившие расклад в индустрии:\n",
            "\n".join(bullets) if bullets else "• Спокойная торговая сессия, внимание смещено в сторону деривативов.",
            "\n📈 **Итоги дня:**",
            "• Институциональная активность остается стабильной.",
            "• Следите за обновлениями крупных L1/L2 сетей.\n",
            "Спокойной ночи! Команда CRYPTO EDITOR продолжает мониторинг 24/7."
        ]

        return {
            "title": "🌙 ВЕЧЕРНИЙ ИТОГ РЫНКА",
            "content": "\n".join(content_lines),
            "post_type": "digest",
            "category": "Digest"
        }

    def generate_educational_insight() -> Dict[str, Any]:
        topics = [
            {
                "title": "🧠 ОНЧЕЙН-ЛИКБЕЗ: Что такое Smart Money и как их отслеживать?",
                "content": "В криптоиндустрии термином **Smart Money** называют кошельки крупных фондов, успешных трейдеров и ранних инвесторов.\n\n**Почему за ними следят?**\nОни первыми реагируют на фундаментальные изменения и имеют доступ к аналитике высшего уровня.\n\n💡 **Инструменты для отслеживания:**\n• **Nansen & Arkham**: позволят повесить алерты на накопление новых токенов.\n• **DeFiLlama**: помогает видеть перетоки ликвидности между экосистемами.\n\n*Вывод:* Наблюдение за Smart Money — это инструмент подтверждения гипотезы, а не слепое копирование сделок."
            },
            {
                "title": "📊 АНАЛИЗ РЫНКА: Зачем смотреть на соотношение TVL и капитализации?",
                "content": "Один из лучших способов оценить переоцененность или недооцененность DeFi-протокола — коэффициент **Mcap / TVL**.\n\n• **Mcap / TVL < 1**: капитализация токена ниже объема средств в протоколе. Часто свидетельствует об условной недооцененности.\n• **Mcap / TVL > 3**: высокая оценка при относительно небольшой реальной ликвидности.\n\n*Совет:* Всегда оценивайте динамику TVL за 30 дней, а не точечную цифру."
            }
        ]
        import random
        selected = random.choice(topics)
        return {
            "title": selected["title"],
            "content": selected["content"],
            "post_type": "educational",
            "category": "Education"
        }
