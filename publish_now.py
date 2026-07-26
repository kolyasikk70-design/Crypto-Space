import asyncio
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from database import Database
from collectors.rss_collector import RSSCollector
from collectors.api_collector import APICollector
from engine.filter_verifier import FilterVerifier
from engine.writer import EditorialWriter
from engine.quality_evaluator import QualityEvaluator
from publisher.telegram_publisher import TelegramPublisher

async def generate_and_publish_real_news():
    db = Database()
    rss = RSSCollector(db)
    api = APICollector(db)
    writer = EditorialWriter()
    evaluator = QualityEvaluator()
    publisher = TelegramPublisher(dry_run=False)

    print("🔎 Fetching REAL fresh news from CoinDesk, Decrypt, Cointelegraph, CryptoSlate...")
    rss_items = await rss.fetch_all()
    api_items = await api.fetch_all()

    all_items = rss_items + api_items
    
    selected_item = None
    selected_category = "General Crypto"

    verifier = FilterVerifier()
    for item in all_items:
        passed, confidence, category = verifier.evaluate_news(item)
        if passed:
            selected_item = item
            selected_category = category
            break

    if not selected_item and all_items:
        selected_item = all_items[0]

    if not selected_item:
        print("❌ No items fetched from feeds.")
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
