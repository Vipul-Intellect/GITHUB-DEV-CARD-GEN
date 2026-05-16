# GitHub Dev Card Generator

An AI-powered developer card generator that turns a public GitHub username into a shareable profile card.

The app uses GitHub profile/repository data, Gemini analysis, Google ADK agent orchestration, and MCP tools to generate a small HTML dev card with the developer's vibe, skills, top repositories, and a fun profile insight.

## What It Does

- Accepts any public GitHub username.
- Fetches GitHub profile and repository data.
- Uses Gemini to analyze the developer profile.
- Generates a styled HTML developer card.
- Saves and serves the card from `/static/cards/{username}.html`.
- Provides a simple browser UI from the same FastAPI backend.
- Includes a direct tool fallback if ADK/MCP orchestration times out.

## Architecture

```text
Browser UI
  -> FastAPI backend
  -> Google ADK agent
  -> MCP toolset over stdio
  -> GitHub API + Gemini
  -> HTML card saved in static/cards
```

The backend exposes:

- `GET /` - web UI
- `GET /health` - health check
- `POST /generate` - generate a dev card
- `GET /card/{username}` - return saved card HTML as JSON
- `GET /static/cards/{username}.html` - open the generated card directly

## Tech Stack

- Python 3.12
- FastAPI
- Uvicorn
- Google ADK
- Gemini
- FastMCP / MCP stdio tools
- GitHub REST API
- Docker
- Google Cloud Run

## Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── mcp_server.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Environment Variables

Create a `.env` file locally:

```env
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GITHUB_TOKEN=optional_github_token
PORT=8080
```

`GITHUB_TOKEN` is optional but recommended to avoid GitHub API rate limits.

Do not commit `.env`. It is ignored by Git and Docker.

## Run Locally

From the project root:

```powershell
cd C:\Users\vtvip\git-dev-card
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
python -m uvicorn main:app --reload --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Run With Docker

From the project root:

```powershell
docker build -t github-dev-card-gen .
docker run --env-file .env -p 8080:8080 github-dev-card-gen
```

Open:

```text
http://127.0.0.1:8080
```

## Deploy To Google Cloud Run

Use the root `Dockerfile` for Cloud Run.

1. Create or select your Google Cloud project.
2. Enable Cloud Run, Cloud Build, and Artifact Registry APIs.
3. Connect this GitHub repository to Cloud Run continuous deployment, or deploy from CLI.
4. Add environment variables in Cloud Run:

```env
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GITHUB_TOKEN=optional_github_token
PORT=8080
```

CLI deployment example:

```powershell
gcloud run deploy github-dev-card-gen `
  --source . `
  --region asia-south1 `
  --allow-unauthenticated `
  --set-env-vars GOOGLE_CLOUD_PROJECT=your_project_id,GOOGLE_CLOUD_LOCATION=us-central1 `
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest
```

If you are not using Secret Manager, set `GOOGLE_API_KEY` directly in the Cloud Run environment variables.

## Notes

- Generated card files are stored on the container filesystem. On Cloud Run, they may disappear when the instance restarts. The `/generate` endpoint can regenerate them anytime.
- The app serves the frontend from FastAPI, so a separate frontend hosting service is not required.
- If ADK/MCP takes too long, the backend falls back to direct tool execution using the same GitHub/Gemini logic.

## Repository

GitHub: <https://github.com/Vipul-Intellect/GITHUB-DEV-CARD-GEN>
