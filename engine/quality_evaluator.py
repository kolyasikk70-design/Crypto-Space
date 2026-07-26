import json
import re
import httpx
from typing import Dict, Any
import config

EVALUATOR_PROMPT = """You are a strict Crypto Editorial Inspector.
Score the following Russian Telegram post on a scale from 1 to 10 across 6 metrics:
1. Originality (Is it rewritten uniquely, without AI cliches?)
2. Accuracy (Are figures, facts, and logic clear?)
3. Importance (Does this actually matter to crypto readers?)
4. Readability (Short paragraphs, clear structure, mobile-friendly?)
5. Virality (Attention-grabbing title and hook?)
6. Clarity (Clear explanation of 'Why it matters' and 'Market implications'?)

Respond ONLY with valid JSON format:
{
  "scores": {
    "originality": 9.5,
    "accuracy": 9.0,
    "importance": 9.0,
    "readability": 9.0,
    "virality": 8.5,
    "clarity": 9.0
  },
  "overall_score": 9.0,
  "passed": true,
  "feedback": "Passes quality checklist."
}
"""

class QualityEvaluator:
    def __init__(self):
        self.threshold = config.QUALITY_SCORE_THRESHOLD

    def _heuristic_score(self, post: Dict[str, Any]) -> Dict[str, Any]:
        title = post.get("title", "")
        content = post.get("content", "")

        forbidden_blocks = ["что произошло", "почему это важно", "влияние на рынок", "итог:", "вывод:", "источник:"]
        has_forbidden_template = any(block in content.lower() for block in forbidden_blocks)

        originality = 4.0 if has_forbidden_template else 9.5
        readability = 9.5 if len(content) >= 150 else 8.0
        virality = 9.0
        clarity = 9.0
        importance = 9.0
        accuracy = 9.5

        scores = {
            "originality": originality,
            "accuracy": accuracy,
            "importance": importance,
            "readability": readability,
            "virality": virality,
            "clarity": clarity
        }
        avg_score = sum(scores.values()) / len(scores)
        passed = avg_score >= self.threshold and not has_forbidden_template

        return {
            "scores": scores,
            "overall_score": round(avg_score, 2),
            "passed": passed,
            "feedback": "Template blocks detected!" if has_forbidden_template else "Passes quality checklist."
        }

    def _clean_json(self, raw_text: str) -> dict:
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        if "```" in raw_text:
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
        match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        if match:
            raw_text = match.group(1)
        return json.loads(raw_text)

    async def evaluate(self, post: Dict[str, Any]) -> Dict[str, Any]:
        if not config.LLM_API_KEY:
            return self._heuristic_score(post)

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                headers = {
                    "Authorization": f"Bearer {config.LLM_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com",
                    "X-Title": "Crypto Engine"
                }

                models_to_try = [config.LLM_MODEL] + [m for m in getattr(config, "FREE_MODELS", []) if m != config.LLM_MODEL]

                for model in models_to_try:
                    try:
                        resp = await client.post(
                            f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions",
                            headers=headers,
                            json={
                                "model": model,
                                "messages": [
                                    {"role": "system", "content": EVALUATOR_PROMPT},
                                    {"role": "user", "content": f"Title: {post.get('title')}\nContent:\n{post.get('content')}"}
                                ],
                                "temperature": 0.1,
                                "provider": {
                                    "allow_fallbacks": False
                                }
                            }
                        )
                        if resp.status_code == 200:
                            content = resp.json()["choices"][0]["message"]["content"]
                            if content:
                                parsed = self._clean_json(content)
                                if "overall_score" in parsed:
                                    return parsed
                    except Exception:
                        continue

        except Exception as e:
            print(f"[QualityEvaluator] LLM evaluation error: {e}. Falling back to heuristic scorer.")

        return self._heuristic_score(post)
