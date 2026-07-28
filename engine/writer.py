import json
import re
import html
import urllib.parse
import httpx
from typing import Dict, Any, Tuple, List
import config

SYSTEM_PROMPT = """Роль: Ты — опытнейший криптоаналитик и шеф-редактор Telegram-канала. Твой стиль — живой, четкий, глубокий, без штампов ИИ и без шаблонности.

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА СТИЛЯ И СТРУКТУРЫ:

1. 😃 ЭМОДЗИ (МАКСИМУМ 2 ШТУКИ, НА БОЛЬШОЙ ПОСТ — 3):
   — Используй СТРОГО МАКСИМУМ 2 эмодзи на стандартный пост (до 3 штук на крупный разбор). 0% эмодзи-спама!

2. 🔀 УНИКАЛЬНАЯ СТРУКТУРА ДЛЯ КАЖДОГО ПОСТА (ЗАПРЕТ НА ОДИНАКОВЫЕ МАКЕТЫ):
   — ❌ КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать посты по одинаковому макету или схеме! Каждый пост должен иметь свой уникальный ритм и композицию.
   — Варьируй подачу: один пост начни с сухих фактов, другой — с прямой речи или вопроса, третий — с выявления скрытой причины, четвертый — с цифр `код`.

3. ✏️ АКТИВНОЕ ИСПОЛЬЗОВАНИЕ ШРИФТОВ И АКЦЕНТОВ:
   — Выделяй ключевые цифры, суммы, глаголы, имена и главные выводы с помощью Markdown: **жирным шрифтом**, `моноширинным кодом` (для адресов/сумм) или *курсивом*. Это делает пост визуально дорогим и легким для восприятия.

4. 🗣️ ИЗБАВЛЯЕМСЯ ОТ «ИИ-ШНОСТИ» И СУХИХ ШТАМПОВ:
   — ПИШИ ЖИВЫМ ЧЕЛОВЕЧЕСКИМ ЯЗЫКОМ. Избегай унылых ИИ-клише («данное событие подчеркивает», «стоит отметить», «рынок замер в ожидании», «инвесторам следует помнить»).
   — Баланс: не пиши как сухой академик и не пиши как глупый школьник. Пиши как дерзкий, но опытный крипто-практик, понимающий подтекст.

5. 🐋 ОНЧЕЙН И КИТЫ (#Ончейн / Whale Alert):
   — ОБЯЗАТЕЛЬНО укажи адрес/кошелек (например: кит `0xc985...`).
   — ОБЯЗАТЕЛЬНО укажи вектор движения: ОТКУДА и КУДА пошли токены (например: с Binance на холодный кошелек).
   — ОБЯЗАТЕЛЬНО разбери направление: «С БИРЖИ НА КОШЕЛЕК» (накопление/бычий знак) ИЛИ «С КОШЕЛЬКА НА БИРЖУ» (продавцы/давление на цену).

6. 🔗 СИНЯЯ ГИПЕРССЫЛКА:
   — В тексте должна быть РОВНО ОДНА синяя ссылка на источник в формате Markdown: `[Название Источника](URL)`. 0% голых ссылок внизу.

ОТВЕТЬ ИСКЛЮЧИТЕЛЬНО В СТРОГОМ ФОРМАТЕ JSON:
{
  "title": "заголовок на русском",
  "content": "живой, структурированный текст поста с акцентами шрифтов, 1-2 эмодзи и одной ссылкой",
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
    def _deduplicate_paragraphs(self, text: str) -> str:
        """Strips duplicate paragraphs from LLM output"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        seen = set()
        unique = []
        for p in paragraphs:
            clean_p = re.sub(r'#[^\s]+', '', p)
            norm = re.sub(r'[^\w]', '', clean_p.lower())
            key = norm[:35]
            if key and key not in seen:
                seen.add(key)
                unique.append(p)
        return "\n\n".join(unique)

    def _inject_referrals(self, content: str) -> Tuple[str, List[str]]:
        used_links = []
        for brand, url in config.REFERRAL_MAP.items():
            if brand.lower() in content.lower() and url:
                used_links.append(f"[{brand}]({url})")
        return content, used_links

    def _clean_ru_title(self, raw_title: str) -> str:
        if not raw_title:
            return "Анализ Крипторынка"
        clean = re.sub(r'```(?:json)?', '', raw_title, flags=re.IGNORECASE)
        clean = re.sub(r'^(?:Заголовок|Title|Тема):\s*', '', clean, flags=re.IGNORECASE)
        clean = clean.replace('"', '').replace("'", '').strip()
        if not self._is_russian(clean):
            clean = self._translate_to_russian(clean)
        return clean if clean else "Анализ Крипторынка"

    def _fallback_generate(self, news_item: Dict[str, Any], category: str) -> Dict[str, Any]:
        title = news_item.get("title", "")
        summary = news_item.get("summary", "")
        source_name = news_item.get("source_name", "Источник")
        source_url = news_item.get("source_url", "")

        ru_title = self._clean_ru_title(title)
        ru_summary = self._translate_to_russian(summary) if summary else ru_title

        # Clean robotic RSS boilerplate & trailing junk
        ru_summary = re.sub(r'\s*–\s*(?:еженедельный обзор|Morning Crypto Report|обзор рынка).*', '', ru_summary, flags=re.IGNORECASE)
        ru_summary = re.sub(r'\[…\]|\[\.\.\.\]|\.\.\.', '', ru_summary).strip()
        ru_summary = re.sub(r'\s{2,}', ' ', ru_summary)

        is_twitter = "twitter" in source_name.lower()
        tag = "📌 #Инсайд" if is_twitter else "📌 #Аналитика"
        author_text = f"[{source_name}]({source_url})" if source_url else source_name

        full_content = (
            f"{tag} **{ru_title}**\n\n"
            f"По материалам {author_text}:\n\n"
            f"{ru_summary}\n\n"
            f"💡 Ключевые показатели указывают на перераспределение ликвидности между большими игроками."
        )

        full_content, refs = self._inject_referrals(full_content)

        return {
            "title": ru_title,
            "content": full_content,
            "post_type": "news",
            "referral_links_used": refs,
            "image_url": news_item.get("image_url")
        }

    def _sanitize_post_content(self, text: str) -> str:
        """Purges any raw JSON metadata keys or wrapper syntax from post text"""
        if not text:
            return ""
        # Regex extraction if raw JSON string was passed
        match = re.search(r'"content"\s*:\s*"([\s\S]*?)"\s*,\s*"(?:post_type|referral_links_used|image_url|title)"', text, re.IGNORECASE)
        if match:
            text = match.group(1).replace('\\"', '"').replace('\\n', '\n')

        text = re.sub(r'^\s*\{\s*"title"\s*:\s*"[^"]*"\s*,\s*"content"\s*:\s*"', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'"\s*,\s*"(?:post_type|referral_links_used|image_url)"[\s\S]*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'"?\s*(?:post_type|referral_links_used|image_url)"\s*:\s*.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\s*\{\s*"title"\s*:\s*.*?\n', '', text, flags=re.IGNORECASE)
        return text.strip('"{}\n\r ')

    def _clean_json(self, raw_text: str) -> dict:
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        match = re.search(r'(\{[\s\S]*\})', raw_text)
        if match:
            json_str = match.group(1)
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and "content" in parsed:
                    parsed["content"] = self._sanitize_post_content(str(parsed["content"]))
                    parsed["title"] = self._clean_ru_title(str(parsed.get("title", "")))
                    return parsed
            except Exception:
                pass

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if lines:
            title = lines[0].replace("#", "").replace("**", "").strip()
            content = "\n\n".join(lines)
            content = self._sanitize_post_content(content)
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
                    "temperature": temperature
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
            r'\[Что прикрепить.*?\n?',
            r'не забудьте проверить.*?\n?',
            r'Оставайтесь в курсе.*?\n?',
            r'.*?всегда готов предложить свои услуги.*?\n?'
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

        source_url = news_item.get('source_url', '')
        is_twitter = "twitter" in source.lower()
        is_onchain = (category == "On-Chain & Whales") or any(k in f"{source} {title} {summary}".lower() for k in ["whale", "lookonchain", "peckshield", "transfer", "wallet", "liquidat"])

        onchain_directive = """
5. 🐋 ДЛЯ ОНЧЕЙН И КИТОВ МАКСИМАЛЬНО ДЕТАЛЬНО УКАЖИ:
   — Адрес/Кошелек (например: кит `0xc985...` или неизвестный адрес).
   — Вектор перевода: ОТКУДА и КУДА пошли токены (например: с биржи Binance на холодный кошелек).
   — Детализируй направление: «С БИРЖИ НА КОШЕЛЕК» (накопление/бычий сигнал) ИЛИ «С КОШЕЛЬКА НА БИРЖУ» (продавцы/давление на цену).
""" if is_onchain else ""

        import random
        style_variations = [
            "ФОРМАТ ПОДАЧИ: 'Молния и Суть' — начни пост с резкого короткого факта, выделяя главные цифры **жирным**, затем раскрой вектор движения рынка.",
            "ФОРМАТ ПОДАЧИ: 'Скрытый Подтекст' — начни с интригующего вопроса или тезиса автора, разбери негласную причину события и подведи экспертный итог.",
            "ФОРМАТ ПОДАЧИ: 'Цифры и Акценты' — подай информацию структурно с акцентом на ключевые параметры `моноширинным кодом` и резкой финальной мыслью с 💡.",
            "ФОРМАТ ПОДАЧИ: 'Аналитический Взгляд' — разбей материал на два живых смысловых блока: факт события ➔ прямая угроза/возможность для держателей."
        ]
        chosen_style = random.choice(style_variations)

        if is_twitter:
            user_prompt = f"""Сделай качественный и глубокий рерайт поста инфлюенсера из Twitter на русском языке, сохраняя смысл и раскрывая подтекст.

Источник: {source}
Ссылка на пост: {source_url}
Автор/Тема: {title}
Текст твита: {summary}

{chosen_style}

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА ДЛЯ ТВИТТЕР-ПОСТА:
1. Заголовок поста должен отражать суть мысли/анонса.
2. В начале или в тексте поста ОБЯЗАТЕЛЬНО укажи автора с интегрированной синей ссылкой в формате Telegram Markdown: `[По данным {source}]({source_url})`.
3. Раскрой не просто текст твита, а его подтекст и смысловую нагрузку для рынка.
4. В конце поста с нового абзаца добавь наши экспертные мысли/вывод с эмодзи 💡.{onchain_directive}
"""
        else:
            user_prompt = f"""Сделай лаконичный, глубокий и экспертный разбор на русском языке по этой новости.

Источник: {source}
Ссылка на источник: {source_url}
Тема: {title}
Детали: {summary}
Категория: {category}

{chosen_style}

ЖЁСТКИЕ ПРАВИЛА:
1. В начале поста ОБЯЗАТЕЛЬНО укажи источник с интегрированной синей ссылкой в формате Telegram Markdown: `[По данным {source}]({source_url})` или `[{source}]({source_url})`.
2. Пост оформляется в выбранном формате подачи.
3. Ровно 1-2 эмодзи на весь пост (до 3 на большой разбор). НИКАКИХ подзаголовков вроде «Вывод:» или «Суть:».
4. 0% ВОДЫ. Только сухая суть, выделение цифр `кодом` или **жирным**.{onchain_directive}
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

                title = self._clean_ru_title(parsed.get("title", title))
                parsed["title"] = title

                content, refs = self._inject_referrals(content)
                
                # Prepend Branded Category Hashtag
                category_hashtags = {
                    "Macro & Regulation": "#Макро",
                    "On-Chain & Whales": "#Ончейн",
                    "Security Alert": "#Безопасность",
                    "Tokenomics & VC": "#Ретродроп",
                    "Infrastructure": "#Инфраструктура",
                    "Twitter Influencer": "#Инсайд",
                    "General Crypto": "#Разбор"
                }
                hashtag = category_hashtags.get(category, "#Инсайд" if "Twitter" in source else "#Разбор")
                
                # Ensure source is hyperlinked ONCE if missing from LLM content
                if source_url and source and "](" not in content:
                    hyperlink = f"[{source}]({source_url})"
                    pattern = re.escape(source)
                    if re.search(pattern, content, flags=re.IGNORECASE):
                        content = re.sub(pattern, hyperlink, content, count=1, flags=re.IGNORECASE)
                    else:
                        content = f"По материалам {hyperlink}:\n\n{content}"

                # Clean any duplicated leading hashtags or emojis from LLM
                if not content.startswith("📌"):
                    content = re.sub(r'^(?:📌|#\w+)*\s*', '', content).strip()
                    content = f"📌 {hashtag} **{title}**\n\n{content}"

                content = self._deduplicate_paragraphs(content)

                # Remove any bottom duplicate source footer or bare URLs at the end of post
                content = re.sub(r'\n+(?:Источник|Ссылка|Source|Link):\s*\[.*?\]\(.*?\)\s*$', '', content, flags=re.IGNORECASE)
                content = re.sub(r'(?<!\()https?://\S+(?!\))', '', content).strip()

                parsed["content"] = content
                parsed["referral_links_used"] = refs
                
                if item_image and not parsed.get("image_url"):
                    parsed["image_url"] = item_image

                return parsed

        except Exception as e:
            print(f"[Writer] Ошибка LLM: {e}. Используем чистый fallback.")

        return self._fallback_generate(news_item, category)
