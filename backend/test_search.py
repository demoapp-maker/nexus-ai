import asyncio
import json

from tools.web_search_tool import web_search_tool


async def test_search():
    print("Testing Web Search Tool...")
    query = "Kenapa dollar naik di mei 2026 ini"
    print(f"Query: {query}")
    
    result = await web_search_tool.search(query)
    print("\nSearch Result:")
    print(json.dumps(result, indent=2))
    
    if "results" in result and len(result["results"]) > 0:
        print("\nSuccessfully found results!")
        # Test fetch URL
        first_url = result["results"][0]["url"]
        print(f"\nTesting URL fetch for: {first_url}")
        content = await web_search_tool.fetch_url_content(first_url)
        print("Content Preview:")
        print(json.dumps(content, indent=2)[:500] + "...")
    else:
        print("\nNo results found. DuckDuckGo might be blocking the request or the selector is wrong.")

if __name__ == "__main__":
    asyncio.run(test_search())
