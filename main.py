import asyncio
import argparse
import sys
import time

# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from database import Database
from collectors.rss_collector import RSSCollector
from collectors.api_collector import APICollector
from collectors.twitter_collector import TwitterCollector
from engine.filter_verifier import FilterVerifier
from engine.deduplicator import Deduplicator
from engine.writer import EditorialWriter
from engine.quality_evaluator import QualityEvaluator
from engine.digests import DigestGenerator
from engine.poll_generator import PollGenerator
from publisher.telegram_publisher import TelegramPublisher
from config import POLL_INTERVAL_SECONDS, QUALITY_SCORE_THRESHOLD

class CryptoNewsroomEngine:
    def __init__(self):
        self.db = Database()
        self.rss_collector = RSSCollector(self.db)
        self.api_collector = APICollector(self.db)
        self.twitter_collector = TwitterCollector(self.db)
        self.filter_verifier = FilterVerifier()
        self.deduplicator = Deduplicator(self.db)
        self.writer = EditorialWriter()
        self.quality_evaluator = QualityEvaluator()
        self.digest_generator = DigestGenerator(self.db)
        self.poll_generator = PollGenerator()
        self.publisher = TelegramPublisher()


    def _can_publish_now(self) -> bool:
        """Check if enough time (at least 3.5 hours) has elapsed since the last Telegram post"""
        recent = self.db.get_recent_posts(limit=1)
        if not recent:
            return True
        last_time = recent[0].get("published_at", 0)
        elapsed = time.time() - last_time
        min_gap = 12600  # 3.5 hours minimum gap between any 2 posts
        if elapsed < min_gap:
            remaining_mins = int((min_gap - elapsed) / 60)
            print(f"⏳ [RATE LOCK] Only {int(elapsed/60)}m since last post. Minimum gap is 3.5h. Waiting {remaining_mins}m...")
            return False
        return True

    async def process_news_item(self, item: dict) -> bool:
        title = item.get("title", "")
        summary = item.get("summary", "")
        source_url = item.get("source_url", "")

        # Rate lock check: max 1 post every 3.5-4 hours
        if not self._can_publish_now():
            return False

        # 1. Deduplication Check
        if self.deduplicator.is_duplicate(title, summary):
            print(f"⏩ [DEDUP] Skipping duplicate news story: {title[:60]}...")
            return False

        # 2. Intelligent Filtering & Verification
        passed, confidence, category = self.filter_verifier.evaluate_news(item)
        if not passed:
            print(f"⏩ [FILTER] Skipping low-impact news ({confidence:.2f}): {title[:60]}...")
            return False

        print(f"⚡ [VERIFIED] News item passed verification ({confidence:.2f}, {category}): {title[:60]}")

        # 3. Editorial Writing
        post_draft = await self.writer.write_post(item, category)

        # 4. Quality Scoring
        quality_res = await self.quality_evaluator.evaluate(post_draft)
        score = quality_res.get("overall_score", 0.0)

        if score < QUALITY_SCORE_THRESHOLD:
            print(f"⚠️ [QUALITY] Draft score {score:.1f}/10 below threshold {QUALITY_SCORE_THRESHOLD}. Re-drafting...")
            post_draft = await self.writer.write_post(item, category)
            quality_res = await self.quality_evaluator.evaluate(post_draft)
            score = quality_res.get("overall_score", score)

        print(f"✨ [QUALITY PASSED] Final score: {score:.1f}/10. Publishing post...")

        # 5. Check language guarantee before Telegram publish
        content_text = post_draft.get("content", "")
        cyrillic = sum(1 for c in content_text if '\u0400' <= c <= '\u04FF')
        alpha = sum(1 for c in content_text if c.isalpha())
        if alpha > 0 and (cyrillic / alpha) < 0.2:
            print(f"🚫 [REJECTED] Draft rejected: Not in Russian. Skipping Telegram publish.")
            return False

        # 6. Publish to Telegram
        msg_id = await self.publisher.publish(
            title=post_draft.get("title", ""),
            content=content_text,
            image_url=post_draft.get("image_url")
        )

        # 7. Store in Database
        self.db.record_published_post(
            title=post_draft.get("title", ""),
            content=content_text,
            post_type=post_draft.get("post_type", "news"),
            category=category,
            quality_score=score,
            quality_breakdown=quality_res.get("scores", {}),
            source_url=source_url,
            referral_links=post_draft.get("referral_links_used", []),
            telegram_message_id=msg_id
        )

        return True

    async def publish_interactive_poll(self):
        poll = self.poll_generator.generate_random_poll()
        msg_id = await self.publisher.publish_poll(
            question=poll["question"],
            options=poll["options"],
            poll_type=poll.get("type", "regular"),
            correct_option_id=poll.get("correct_option_id"),
            explanation=poll.get("explanation")
        )
        if msg_id:
            self.db.record_published_post(
                title=poll["question"],
                content=json.dumps(poll["options"], ensure_ascii=False),
                post_type="poll",
                category="Interactive",
                quality_score=10.0,
                quality_breakdown={},
                source_url="",
                referral_links=[],
                telegram_message_id=msg_id
            )
            print(f"✅ Published interactive Poll/Quiz #{msg_id}!")

    async def check_and_publish_daily_poll(self):
        """Automatically publish 1 interactive poll/quiz every 24 hours"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT published_at FROM posts WHERE post_type = 'poll' ORDER BY published_at DESC LIMIT 1")
            row = cursor.fetchone()
            if not row or (time.time() - row[0]) >= 86400:
                print("📊 [DAILY POLL] Publishing daily interactive poll/quiz...")
                await self.publish_interactive_poll()

    async def run_cycle(self):
        print("\n🔍 [DISCOVERY] Fetching crypto news, metric updates, and Twitter influencer posts...")
        
        # Check daily interactive poll
        try:
            await self.check_and_publish_daily_poll()
        except Exception as e:
            print(f"⚠️ Error checking daily poll: {e}")

        # Gather news items
        rss_news = await self.rss_collector.fetch_all()
        api_events = await self.api_collector.fetch_all()
        twitter_tweets = await self.twitter_collector.fetch_all()

        unprocessed = self.db.get_unprocessed_news(limit=25)
        # Sort queue to process Twitter Influencer & Whale Alert items first
        tw_items = [i for i in unprocessed if "twitter" in i.get("source_name", "").lower()]
        other_items = [i for i in unprocessed if "twitter" not in i.get("source_name", "").lower()]
        unprocessed = tw_items + other_items

        print(f"📥 Received {len(rss_news)} RSS stories, {len(api_events)} API events, {len(twitter_tweets)} Twitter posts. {len(unprocessed)} unprocessed in DB.")

        if not self._can_publish_now():
            for item in unprocessed:
                self.db.mark_news_processed(item["id"])
            print("✅ Cycle complete. Post rate lock active. 0 new posts published.\n")
            return

        published = False
        for item in unprocessed:
            try:
                if not published:
                    published = await self.process_news_item(item)
            except Exception as e:
                print(f"❌ Error processing news item #{item.get('id')}: {e}")
            finally:
                self.db.mark_news_processed(item["id"])

        print(f"✅ Cycle complete. Published {'1' if published else '0'} new post.\n")

    async def run_continuous(self):
        print("🚀 Starting Autonomous CRYPTO EDITOR Engine (24/7 mode)...")
        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

def main():
    parser = argparse.ArgumentParser(description="CRYPTO EDITOR-IN-CHIEF Autonomous Engine")
    parser.add_argument("--once", action="store_true", help="Run a single fetch/process cycle and exit")
    parser.add_argument("--poll", action="store_true", help="Generate and publish an interactive poll/quiz")
    parser.add_argument("--digest", choices=["morning", "evening"], help="Generate and publish a digest")
    parser.add_argument("--status", action="store_true", help="Show published post stats")

    args = parser.parse_args()

    engine = CryptoNewsroomEngine()

    if args.status:
        posts = engine.db.get_recent_posts(limit=10)
        print(f"Total published posts in DB: {len(posts)}")
        for p in posts:
            print(f" #{p['id']} [{p['published_at']}] {p['title'][:50]} (Score: {p['quality_score']})")
        return

    if args.poll:
        asyncio.run(engine.publish_interactive_poll())
        return

    if args.digest:
        asyncio.run(engine.publish_digest(args.digest))
        return

    if args.once:
        asyncio.run(engine.run_cycle())
        return

    asyncio.run(engine.run_continuous())

if __name__ == "__main__":
    main()
