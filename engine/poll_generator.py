import random
from typing import Dict, Any, List

class PollGenerator:
    def __init__(self):
        self.market_polls = [
            {
                "question": "📊 Куда пойдет цена Биткоина в ближайшие 7 дней?",
                "options": ["🚀 Пробой вверх к новым максимумам", "🐻 Коррекция и тест поддержек", "💤 Консолидация и флэт"],
                "type": "regular"
            },
            {
                "question": "🔥 Какой экосистеме вы отдаете приоритет в этом месяце?",
                "options": ["⚡ Solana", "🌐 Ethereum & L2", "🟣 Base & Monad", "💎 Вне рынка / в стейблах"],
                "type": "regular"
            },
            {
                "question": "🐋 Где вы держите основную часть своего крипто-порта?",
                "options": ["🔒 Холодные кошельки (Ledger/Trezor)", "💼 Некастодиальные софт-кошельки", "🏛 Централизованные биржи (CEX)"],
                "type": "regular"
            }
        ]

        self.educational_quizzes = [
            {
                "question": "🧠 КВИЗ: Что такое термин MVRV в ончейн-анализе?",
                "options": [
                    "Отношение рыночной капитализации к реализованной",
                    "Объем выводимых монет с бирж",
                    "Процент токенов в стейкинге"
                ],
                "type": "quiz",
                "correct_option_id": 0,
                "explanation": "MVRV (Market Value to Realized Value) показывает отношение текущей капитализации к стоимости покупки всех монет."
            },
            {
                "question": "🧠 КВИЗ: Какая разница между L1 и L2 сетями?",
                "options": [
                    "L2 обрабатывает транзакции вне основного блокчейна для масштабирования",
                    "L1 работает только со смарт-контрактами, а L2 — только с переводами",
                    "L2 не использует никакой криптографии"
                ],
                "type": "quiz",
                "correct_option_id": 0,
                "explanation": "L2 (Layer 2) — это решение масштабирования, обрабатывающее транзакции поверх базного L1 блокчейна."
            }
        ]

    def generate_random_poll(self) -> Dict[str, Any]:
        all_options = self.market_polls + self.educational_quizzes
        return random.choice(all_options)
