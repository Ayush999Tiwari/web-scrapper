import asyncio
from core.orchestrator import scrape_url
from core.url_validator import validate_url
async def main():
    url = input("Enter URL: ")
    try:
        url = validate_url(url)
    except Exception as e:
        print("Invalid URL:", e)
        return
    result = await scrape_url(url)
    print("\n RESULT ")
    print("Engine:", result.engine_used)
    print("Status:", result.status)
    print("Title:", result.title)
    print("Length:", len(result.content or ""))
    print("\nPreview:\n", (result.content or "No content"))
if __name__ == "__main__":
    asyncio.run(main())