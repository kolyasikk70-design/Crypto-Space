import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'd:/anal')
from engine.writer import EditorialWriter

async def test():
    writer = EditorialWriter()
    item = {
        "title": "Bitcoin ETFs shed $225M, snapping seven-day inflow streak as crypto market cools",
        "summary": "Bitcoin ETFs saw $225 million in outflows on Friday, ending seven consecutive days of inflows. BlackRock's IBIT led with $186M in redemptions.",
        "source_name": "CoinDesk",
        "source_url": "https://coindesk.com/test"
    }
    print(f'Testing writer...')
    post = await writer.write_post(item, 'Macro & Regulation')
    print('=== RESULT ===')
    t = post.get("title", "")
    c = post.get("content", "")
    print(f'Title: {t}')
    print(f'Content:\n{c}')

asyncio.run(test())
