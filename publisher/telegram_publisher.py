import httpx
import asyncio
import re
from typing import Optional, Dict, Any
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN

class TelegramPublisher:
    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID, dry_run: bool = DRY_RUN):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.dry_run = dry_run or not bool(bot_token and chat_id)

    def _strip_markdown(self, text: str) -> str:
        """Removes basic Markdown formatting for plain text fallback"""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        return text

    async def publish(self, title: str, content: str, parse_mode: str = "Markdown", image_url: Optional[str] = None) -> Optional[int]:
        """
        Publishes post to Telegram channel. Handles text, photo, caption length limits, and syntax fallbacks.
        """
        full_text = content

        if self.dry_run:
            print("\n=================== [DRY RUN TELEGRAM PUBLISH] ===================")
            print(f"CHAT_ID: {self.chat_id or 'CONSOL_ONLY'}")
            print(f"IMAGE_URL: {image_url or 'None'}")
            print(f"PARSE_MODE: {parse_mode}")
            print("------------------------------------------------------------------")
            print(full_text)
            print("==================================================================\n")
            return 99999  # Mock Telegram message ID

        # Telegram Photo Caption Limit is 1024 characters.
        # If text > 1020 chars and image_url is provided, fallback to text-only message (4096 char limit)
        if image_url and len(full_text) > 1020:
            print("[TelegramPublisher] Content length > 1020 chars. Switching from sendPhoto to sendMessage to avoid Telegram caption error.")
            image_url = None

        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto" if image_url else f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "parse_mode": parse_mode
        }

        if image_url:
            payload["photo"] = image_url
            payload["caption"] = full_text
        else:
            payload["text"] = full_text
            payload["disable_web_page_preview"] = False

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    msg_id = data.get("result", {}).get("message_id")
                    print(f"[TelegramPublisher] Successfully published post #{msg_id} to Telegram!")
                    return msg_id
                
                # If image fails, retry as text message
                if image_url:
                    print(f"[TelegramPublisher] Photo send failed ({response.status_code}). Retrying plain text message...")
                    return await self.publish(title=title, content=content, parse_mode=parse_mode, image_url=None)

                # If Markdown parsing failed, retry plain text without parse_mode
                if response.status_code == 400 and "parse" in response.text.lower():
                    print("[TelegramPublisher] Markdown parsing error in Telegram API. Retrying without parse_mode...")
                    plain_text = self._strip_markdown(full_text)
                    retry_payload = {
                        "chat_id": self.chat_id,
                        "text": plain_text,
                        "disable_web_page_preview": False
                    }
                    retry_resp = await client.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=retry_payload)
                    if retry_resp.status_code == 200:
                        msg_id = retry_resp.json().get("result", {}).get("message_id")
                        print(f"[TelegramPublisher] Successfully published plain text post #{msg_id}!")
                        return msg_id

                print(f"[TelegramPublisher] API error ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"[TelegramPublisher] Failed to publish post: {e}")

        return None

    async def publish_poll(self, question: str, options: list, poll_type: str = "regular", correct_option_id: Optional[int] = None, explanation: Optional[str] = None) -> Optional[int]:
        """
        Publishes an interactive poll or quiz to Telegram.
        """
        if self.dry_run:
            print("\n=================== [DRY RUN TELEGRAM POLL] ===================")
            print(f"QUESTION: {question}")
            print(f"OPTIONS: {options}")
            print(f"TYPE: {poll_type}")
            print("===============================================================\n")
            return 99998  # Mock Poll ID

        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendPoll"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "question": question[:300],
            "options": options,
            "is_anonymous": True,
            "type": poll_type
        }

        if poll_type == "quiz" and correct_option_id is not None:
            payload["correct_option_id"] = correct_option_id
            if explanation:
                payload["explanation"] = explanation[:200]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    msg_id = resp.json().get("result", {}).get("message_id")
                    print(f"[TelegramPublisher] Successfully published Poll #{msg_id}!")
                    return msg_id
                else:
                    print(f"[TelegramPublisher] Poll API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[TelegramPublisher] Failed to publish poll: {e}")

        return None
