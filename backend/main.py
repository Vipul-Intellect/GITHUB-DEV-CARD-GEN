from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from google.genai import types

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

# ADK Imports
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from agent import github_card_agent
from mcp_server import analyze_profile, generate_card_html, save_card, scrape_github

app = FastAPI(title="GitHub Dev Card Generator API")
STATIC_DIR = BACKEND_DIR / "static"
STATIC_CARDS_DIR = STATIC_DIR / "cards"
FRONTEND_INDEX = BACKEND_DIR.parent / "frontend" / "index.html"

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Ensure static directory exists
STATIC_CARDS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class GenerateRequest(BaseModel):
    username: str

async def _generate_card_direct(username: str) -> dict:
    """Reliable non-agent fallback using the same MCP tool functions directly."""
    github_data = await scrape_github(username)
    if github_data.get("error"):
        raise HTTPException(status_code=404, detail=github_data["error"])

    analysis = await analyze_profile(github_data)
    card_html = await generate_card_html(username, github_data, analysis)
    card_url = await save_card(username, card_html)

    card_file = STATIC_CARDS_DIR / f"{username}.html"
    html_content = card_file.read_text(encoding="utf-8") if card_file.exists() else card_html

    return {
        "status": "success",
        "message": "Generated with direct tool fallback.",
        "card_url": card_url,
        "html": html_content,
        "source": "direct_tools",
    }

def _render_index_html() -> str:
    """Serve the frontend from the API host when no separate frontend is deployed."""
    if FRONTEND_INDEX.exists():
        html = FRONTEND_INDEX.read_text(encoding="utf-8")
        return html.replace("${BACKEND_URL}", "")

    return """
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>GitHub Dev Card Generator</title>
        <style>
            body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0d1117; color: #c9d1d9; font-family: system-ui, sans-serif; }
            main { width: min(560px, calc(100vw - 32px)); padding: 32px; border: 1px solid #30363d; border-radius: 20px; background: #161b22; text-align: center; }
            input { width: 65%; padding: 12px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; }
            button { padding: 12px 18px; border: 0; border-radius: 10px; background: #2ea44f; color: white; font-weight: 700; cursor: pointer; }
            #result { margin-top: 24px; }
            .error { color: #ff7b72; }
        </style>
    </head>
    <body>
        <main>
            <h1>GitHub Dev Card Generator</h1>
            <p>Enter a public GitHub username.</p>
            <input id="username" placeholder="torvalds" />
            <button onclick="generate()">Generate</button>
            <div id="result"></div>
        </main>
        <script>
            async function generate() {
                const username = document.getElementById("username").value.trim();
                const result = document.getElementById("result");
                if (!username) { result.innerHTML = '<p class="error">Please enter a username.</p>'; return; }
                result.textContent = "Generating...";
                try {
                    const response = await fetch("/generate", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ username })
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.detail || data.error || "API error");
                    result.innerHTML = data.html || `<a href="${data.card_url}">Open card</a>`;
                } catch (error) {
                    result.innerHTML = `<p class="error">${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_render_index_html())

@app.get("/index.html", response_class=HTMLResponse)
async def index_html():
    return HTMLResponse(_render_index_html())

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/card/{username}")
async def get_card(username: str):
    file_path = STATIC_CARDS_DIR / f"{username}.html"
    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as f:
            return {"html": f.read()}
    raise HTTPException(status_code=404, detail="Card not found")

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    agent_error = None
    try:
        # Create a Runner instance
        runner = Runner(
            app_name="github_dev_card",
            agent=github_card_agent,
            session_service=session_service,
            memory_service=memory_service,
            auto_create_session=True,
        )

        final_response = ""
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate a dev card for user: {username}")],
        )

        # Run the agent with specific instruction
        async for event in runner.run_async(
            user_id=username,
            session_id=username,
            new_message=user_message,
        ):
            # Capture the final text output which should contain the URL
            if hasattr(event, 'text') and event.text:
                final_response += event.text
            elif getattr(event, "content", None) and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_response += part.text

        # Fetch the saved HTML content to return as well
        card_file = STATIC_CARDS_DIR / f"{username}.html"
        html_content = ""
        if card_file.exists():
            with card_file.open("r", encoding="utf-8") as f:
                html_content = f.read()

        if not html_content:
            print("[Generate] Agent completed without saving a card; using direct fallback.")
            return await _generate_card_direct(username)

        return {
            "status": "success",
            "message": final_response,
            "card_url": f"/static/cards/{username}.html",
            "html": html_content,
            "source": "adk_agent",
        }
    except Exception as e:
        agent_error = str(e)
        print(f"[Generate] Agent path failed, trying direct fallback: {agent_error}")

    try:
        result = await _generate_card_direct(username)
        result["agent_error"] = agent_error
        return result
    except HTTPException:
        raise
    except Exception as fallback_error:
        print(f"Error in /generate fallback: {fallback_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Card generation failed. Agent error: {agent_error}; fallback error: {fallback_error}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
