from mcp.server.fastmcp import FastMCP
import httpx
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash") 

mcp = FastMCP("GitHubDevCardTools")

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Scrapes GitHub profile and repo data."""
    async with httpx.AsyncClient() as client:
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            
        # Profile Info
        profile_res = await client.get(f"https://api.github.com/users/{username}", headers=headers)
        if profile_res.status_code != 200:
            return {"error": f"User {username} not found"}
        
        profile = profile_res.json()
        
        # Repos Info
        repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30", headers=headers)
        repos_data = repos_res.json() if repos_res.status_code == 200 else []
        
        # Process Repos
        top_repos = []
        languages = {}
        for r in sorted(repos_data, key=lambda x: x.get('stargazers_count', 0), reverse=True)[:6]:
            top_repos.append({
                "name": r.get("name"),
                "stars": r.get("stargazers_count"),
                "language": r.get("language"),
                "description": r.get("description")
            })
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "name": profile.get("name") or username,
            "bio": profile.get("bio"),
            "location": profile.get("location"),
            "public_repos": profile.get("public_repos"),
            "followers": profile.get("followers"),
            "avatar_url": profile.get("avatar_url"),
            "top_repos": top_repos,
            "most_used_languages": sorted(languages, key=languages.get, reverse=True)[:5]
        }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Analyzes GitHub data using Gemini to generate a personality profile."""
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object with:
    - developer_vibe: A 1-sentence personality description.
    - top_skills: A list of exactly 3 technical skills.
    - fun_fact: A clever observation based on their repos.
    - card_theme: One of ["hacker", "builder", "researcher", "designer", "open-source-hero"]

    Data: {json.dumps(github_data)}
    """
    response = model.generate_content(prompt)
    # Extract JSON from response (handling potential markdown wrappers)
    text = response.text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    return json.loads(text)

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generates a beautiful HTML string for a dev card."""
    theme = analysis.get("card_theme", "hacker")
    
    themes = {
        "hacker": "bg-black text-green-400 border-green-500 font-mono",
        "builder": "bg-blue-900 text-white border-blue-400 font-sans",
        "researcher": "bg-slate-100 text-slate-900 border-slate-400 font-serif",
        "designer": "bg-gradient-to-br from-pink-500 to-purple-600 text-white border-white",
        "open-source-hero": "bg-orange-500 text-white border-orange-200"
    }
    
    theme_class = themes.get(theme, themes["hacker"])
    
    skills_html = "".join([f'<span class="px-2 py-1 rounded bg-white/20 text-xs m-1">{s}</span>' for s in analysis.get("top_skills", [])])
    repos_html = "".join([f'<div class="text-xs mb-1">⭐ {r["stars"]} - <b>{r["name"]}</b>: {r["language"]}</div>' for r in github_data.get("top_repos", [])[:3]])

    html = f"""
    <div class="max-w-sm rounded-2xl border-2 p-6 {theme_class} shadow-2xl">
        <div class="flex items-center space-x-4 mb-4">
            <img src="{github_data.get('avatar_url')}" class="w-16 h-16 rounded-full border-2 border-current" />
            <div>
                <h2 class="text-xl font-bold">{github_data.get('name')}</h2>
                <p class="text-xs opacity-80">@{username}</p>
            </div>
        </div>
        <p class="text-sm italic mb-4">"{analysis.get('developer_vibe')}"</p>
        <div class="flex flex-wrap mb-4">
            {skills_html}
        </div>
        <div class="grid grid-cols-2 gap-2 text-xs mb-4">
            <div class="p-2 bg-white/10 rounded"><b>Repos:</b> {github_data.get('public_repos')}</div>
            <div class="p-2 bg-white/10 rounded"><b>Followers:</b> {github_data.get('followers')}</div>
        </div>
        <div class="mb-4">
            <h3 class="text-xs font-bold uppercase tracking-wider mb-2">Top Projects</h3>
            {repos_html}
        </div>
        <div class="text-[10px] opacity-60 mt-4 border-t border-current pt-2">
            <b>Fun Fact:</b> {analysis.get('fun_fact')}
        </div>
    </div>
    """
    return html

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Saves the card HTML to static/cards and returns the path."""
    static_dir = BACKEND_DIR / "static" / "cards"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Full self-contained HTML
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #111; }}</style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    file_path = static_dir / f"{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
