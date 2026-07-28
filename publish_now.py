import asyncio
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from database import Database
from collectors.rss_collector import RSSCollector
from collectors.api_collector import APICollector
from collectors.twitter_collector import TwitterCollector
from engine.filter_verifier import FilterVerifier
from engine.writer import EditorialWriter
from engine.quality_evaluator import QualityEvaluator
from publisher.telegram_publisher import TelegramPublisher

async def generate_and_publish_real_news():
    db = Database()
    rss = RSSCollector(db)
    api = APICollector(db)
    twitter = TwitterCollector(db)
    writer = EditorialWriter()
    evaluator = QualityEvaluator()
    publisher = TelegramPublisher(dry_run=False)

    print("🔎 Fetching REAL fresh news from RSS feeds, Twitter, and DB...")
    rss_items = await rss.fetch_all()
    api_items = await api.fetch_all()
    twitter_items = await twitter.fetch_all()

    unprocessed_db = db.get_unprocessed_news(limit=20)

    # Fallback to raw_news table if all entries are already seen
    if not rss_items and not twitter_items and not unprocessed_db:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_name, source_url, title, summary FROM news_raw ORDER BY id DESC LIMIT 15")
            rows = cursor.fetchall()
            for r in rows:
                rss_items.append({
                    "source_name": r[0],
                    "source_url": r[1],
                    "title": r[2],
                    "summary": r[3]
                })

    all_items = twitter_items + rss_items + api_items + unprocessed_db
    scored_items = []
    verifier = FilterVerifier()
    for item in all_items:
        passed, confidence, category = verifier.evaluate_news(item)
        if passed:
            scored_items.append((confidence, item, category))

    # Sort descending by high-impact confidence score!
    scored_items.sort(key=lambda x: x[0], reverse=True)

    selected_item = None
    selected_category = "General Crypto"

    if scored_items:
        best_score, selected_item, selected_category = scored_items[0]
        print(f"🔥 TOP IMPACT ITEM SELECTED (Score: {best_score:.2f}) [{selected_category}]: {selected_item.get('title')[:80]}")

    if not selected_item and all_items:
        selected_item = all_items[0]

    if not selected_item:
        print("❌ No items fetched from feeds or DB.")
        return

    print(f"\n📌 REAL SOURCE: [{selected_item.get('source_name')}] {selected_item.get('source_url')}")
    print(f"📌 REAL TITLE: {selected_item.get('title')}")
    print("✍️ Generating Russian post from REAL verified data...")
    
    post = await writer.write_post(selected_item, selected_category)
    
    print("\n=================== GENERATED POST ===================")
    print(f"TITLE: {post.get('title')}")
    print(f"CONTENT:\n{post.get('content')}")
    print("======================================================\n")

    print("📱 Publishing real post directly to Telegram channel...")
    msg_id = await publisher.publish(
        title=post.get("title", ""),
        content=post.get("content", ""),
        image_url=post.get("image_url")
    )

    if msg_id:
        print(f"✅ REAL POST PUBLISHED SUCCESSFULLY! Message ID: #{msg_id}")
    else:
        print("❌ Failed to publish to Telegram.")

if __name__ == "__main__":
    asyncio.run(generate_and_publish_real_news())
