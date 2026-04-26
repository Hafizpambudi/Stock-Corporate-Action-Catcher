import asyncio
from scrapling.fetchers import AsyncStealthySession

async def test():
    async with AsyncStealthySession(headless=True) as session:
        response = await session.fetch('https://example.com')
        print("Response type:", type(response))
        print("Attributes:", [a for a in dir(response) if not a.startswith('_')])
        # Check for page attribute
        if hasattr(response, 'page'):
            print("Has page attribute")
        else:
            print("No page attribute")
        # Try to find the underlying page
        print("Response internal vars:", vars(response))

asyncio.run(test())
