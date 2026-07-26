import json
import re
import html
import urllib.parse
import httpx
from typing import Dict, Any, Tuple, List
import config

SYSTEM_PROMPT = """Роль: Ты — ведущий криптоаналитик и главный автор популярного Telegram-канала. Твой стиль — «свой среди своих»: динамичный, глубокий, уверенный, экспертный и бодрый.

ПРАВИЛА НАПИСАНИЯ:

1. ТЕМАТИКА И ТРАФИК (САМОЕ ВАЖНОЕ И ХАЙПОВОЕ):
   — Каждый пост должен быть на РАЗНУЮ и самую горячую тему: срочные новости рынка, фатальные взломы/этичные хаки, макроэкономика (ФРС, SEC, ETF), громкие аирдропы и разблокировки, тренды экосистем (Solana, Base, Monad, L2), движение китов и Smart Money.
   — Бери только то, что реально волнует индустрию прямиком сейчас.

2. НИКАКИХ ШАБЛОННЫХ ПОДЗАГОЛОВКОВ (ЖЁСТКИЙ ЗАПРЕТ):
   — КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ повторные метки:
     ❌ «Главные цифры дня:»
     ❌ «Вывод:»
     ❌ «Мое мнение:»
     ❌ «Суть события:»
     ❌ «Контекст рынка:»
     ❌ «Основное:»
     ❌ «Итог:»
   — Пост — это ЕДИНЫЙ ЖИВОЙ ТЕКСТ. Абзацы по 1–3 предложения, разделенные пустой строкой.

3. ТОЧНОСТЬ ФАКТОВ И ЦЕН (СТРОГО):
   — НИКОГДА НЕ ВЫДУМЫВАЙ ЦЕНЫ, цифры или статистику.
   — Используй ТОЛЬКО те данные, цены и факты, которые переданы в источнике или запросе.

4. ЭМОДЗИ И ЖИВАЯ ПОДАЧА:
   — Используй эмодзи (📊 🚀 ⚡ 💎 🚨 📌 🧠 📉 💡 🔥 🐋) как яркие визуальные акценты для чтения с телефона.
   — Разнообразь подачи: иногда срочная молния, иногда аналитический разбор, иногда ироничный взгляд на тренд.
   — Если просишь фидбек, делай это естественно, разно и не в каждом посте.

ОТВЕТЬ ИСКЛЮЧИТЕЛЬНО В СТРОГОМ ФОРМАТЕ JSON:
{
  "title": "заголовок на русском",
  "content": "готовый живой текст поста на русском без шаблонных подзаголовков",
  "post_type": "news",
  "referral_links_used": [],
  "image_url": null
}
"""


class EditorialWriter:
    def __init__(self):
        pass

    def _is_russian(self, text: str) -> bool:
        cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        alpha = sum(1 for c in text if c.isalpha())
        return (cyrillic / alpha) >= 0.25 if alpha > 0 else False

    def _translate_to_russian(self, text: str) -> str:
        if not text:
            return ""
        if self._is_russian(text):
            return text
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ru&dt=t&q={urllib.parse.quote(text)}"
            resp = httpx.get(url, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                translated = "".join([part[0] for part in data[0] if part and part[0]])
                return translated.strip()
        except Exception:
            pass
        return text

    def _inject_referrals(self, content: str) -> Tuple[str, List[str]]:
        used_links = []
        for brand, url in config.REFERRAL_MAP.items():
            if brand.lower() in content.lower() and url:
                used_links.append(f"[{brand}]({url})")
        return content, used_links

    def _fallback_generate(self, news_item: Dict[str, Any], category: str) -> Dict[str, Any]:
        title = news_item.get("title", "")
        summary = news_item.get("summary", "")

        ru_title = self._translate_to_russian(title)
        ru_summary = self._translate_to_russian(summary[:450]) if summary else ru_title

        full_content = f"**{ru_title}**\n\n{ru_summary}"
        full_content, refs = self._inject_referrals(full_content)

        return {
            "title": ru_title,
            "content": full_content,
            "post_type": "news",
            "referral_links_used": refs,
            "image_url": news_item.get("image_url")
        }

    def _clean_json(self, raw_text: str) -> dict:
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        match = re.search(r'(\{[\s\S]*\})', raw_text)
        if match:
            json_str = match.group(1)
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and "content" in parsed:
                    return parsed
            except Exception:
                pass

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if lines:
            title = lines[0].replace("#", "").replace("**", "").strip()
            content = "\n\n".join(lines)
            return {
                "title": title,
                "content": content,
                "post_type": "news",
                "referral_links_used": [],
                "image_url": None
            }

        raise ValueError("Empty response from LLM")

    async def _call_llm(self, client: httpx.AsyncClient, messages: list, temperature: float = 0.4) -> str:
        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Crypto Engine"
        }

        models_to_try = [config.LLM_MODEL] + [m for m in getattr(config, "FREE_MODELS", []) if m != config.LLM_MODEL]
        last_error = ""

        for model in models_to_try:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "provider": {
                        "allow_fallbacks": False
                    }
                }
                response = await client.post(
                    f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    if content:
                        print(f"[Writer] Successfully called free model: {model}")
                        return content
                else:
                    last_error = f"{model}: {response.status_code} {response.text[:150]}"
            except Exception as ex:
                last_error = f"{model}: {ex}"

        raise Exception(f"All LLM models failed. Last error: {last_error}")

    def _purge_template_headers(self, text: str) -> str:
        forbidden_patterns = [
            r'📌\s*\*?Суть события:\*?',
            r'💡\s*\*?Контекст рынка:\*?',
            r'📊\s*\*?Главные цифры дня:\*?',
            r'🧠\s*\*?Вывод:\*?',
            r'🧠\s*\*?Мое мнение:\*?',
            r'🔑\s*\*?Основное:\*?',
            r'📌\s*\*?Итог:\*?',
            r'💬\s*Что думаете.*?\n?',
            r'\[Что прикрепить.*?\n?'
        ]
        for pattern in forbidden_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    async def write_post(self, news_item: Dict[str, Any], category: str) -> Dict[str, Any]:
        if not config.LLM_API_KEY:
            return self._fallback_generate(news_item, category)

        title = news_item.get('title', '')
        summary = news_item.get('summary', '')
        source = news_item.get('source_name', '')
        item_image = news_item.get('image_url')

        user_prompt = f"""Сделай яркий, глубокий и хайповый разбор на русском языке по этой новости.

Источник: {source}
Тема: {title}
Детали: {summary}
Категория: {category}

Рефeral-ссылки: {json.dumps(config.REFERRAL_MAP, ensure_ascii=False)}

ЖЁСТКИЕ ПРАВИЛА:
— НИКАКИХ ШАБЛОННЫХ ПОДЗАГОЛОВКОВ («Главные цифры дня:», «Вывод:», «Мое мнение:», «Суть:»).
— Разные форматы подачи: аналитика, молния, разбор хайпа, разбор тренда.
— Сочные акценты с эмодзи.
"""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]

                raw = await self._call_llm(client, messages, temperature=0.4)
                parsed = self._clean_json(raw)
                content = parsed.get("content", "")
                content = self._purge_template_headers(content)

                if not self._is_russian(content):
                    print(f"[Writer] ⚠️ Перевод ответа модели на русский...")
                    content = self._translate_to_russian(content)
                    title = self._translate_to_russian(parsed.get("title", ""))
                    parsed["title"] = title

                content, refs = self._inject_referrals(content)
                
                # Prepend Branded Category Hashtag
                category_hashtags = {
                    "Macro & Regulation": "#Макро",
                    "On-Chain & Whales": "#Ончейн",
                    "Security Alert": "#Безопасность",
                    "Tokenomics & VC": "#Ретродроп",
                    "Infrastructure": "#Инфраструктура",
                    "General Crypto": "#Разбор"
                }
                hashtag = category_hashtags.get(category, "#Разбор")
                if not content.startswith("#"):
                    content = f"{hashtag} {content}"

                parsed["content"] = content
                parsed["referral_links_used"] = refs
                
                if item_image and not parsed.get("image_url"):
                    parsed["image_url"] = item_image

                return parsed

        except Exception as e:
            print(f"[Writer] Ошибка LLM: {e}. Используем чистый fallback.")

        return self._fallback_generate(news_item, category)
