import asyncio
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from engine.writer import EditorialWriter
from engine.poll_generator import PollGenerator
from publisher.telegram_publisher import TelegramPublisher

async def test_new_features():
    writer = EditorialWriter()
    poll_gen = PollGenerator()
    publisher = TelegramPublisher()

    print("=== 1. TEST BRANDED HASHTAG NAVIGATOR ===")
    item = {
        'source_name': 'CoinDesk',
        'source_url': 'https://coindesk.com',
        'title': 'Bitcoin ETFs see major inflows as institutional buyers return',
        'summary': 'BlackRock and Fidelity spot Bitcoin ETFs record $350 million in daily inflows.',
        'image_url': 'https://cdn.sanity.io/images/s3y3vcno/production/ba52f7bccf2ae307a3c4c7efe5945ed295f5380d-4032x2268.jpg'
    }
    post = await writer.write_post(item, 'Macro & Regulation')
    print("Generated Post Content:\n", post.get("content"))

    print("\n=== 2. TEST INTERACTIVE TELEGRAM POLL ===")
    poll = poll_gen.generate_random_poll()
    print("Selected Poll Question:", poll["question"])
    print("Poll Options:", poll["options"])

    msg_id = await publisher.publish_poll(
        question=poll["question"],
        options=poll["options"],
        poll_type=poll.get("type", "regular"),
        correct_option_id=poll.get("correct_option_id"),
        explanation=poll.get("explanation")
    )
    print("Poll Dry Run Test Finished cleanly!")

if __name__ == "__main__":
    asyncio.run(test_new_features())
