import asyncio
import json
import os
from mcp_server import scrape_github, analyze_profile, generate_card_html

async def main():
    username = "torvalds"
    print(f"--- Step 1: Scraping GitHub for '{username}' ---")
    try:
        github_data = await scrape_github(username)
        if "error" in github_data:
            print(f"Error scraping profile: {github_data['error']}")
            return
        print("Success: Data fetched.")
        # print(json.dumps(github_data, indent=2))
    except Exception as e:
        print(f"FAILED Step 1: {e}")
        return

    print(f"\n--- Step 2: Analyzing Profile with Gemini ---")
    try:
        analysis = await analyze_profile(github_data)
        print("Success: Analysis complete.")
        # print(json.dumps(analysis, indent=2))
    except Exception as e:
        print(f"FAILED Step 2: {e}")
        return

    print(f"\n--- Step 3: Generating HTML Card ---")
    try:
        html = await generate_card_html(username, github_data, analysis)
        print("Success: HTML generated.")
    except Exception as e:
        print(f"FAILED Step 3: {e}")
        return

    print("\n--- Step 4: Final Results ---")
    print(f"Card Theme: {analysis.get('card_theme')}")
    print(f"Developer Vibe: {analysis.get('developer_vibe')}")

if __name__ == "__main__":
    asyncio.run(main())
