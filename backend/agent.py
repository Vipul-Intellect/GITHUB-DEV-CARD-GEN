import os
import sys
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Path to the MCP server
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# Configure MCP Toolset with stdio transport
mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER_PATH],
            cwd=os.path.dirname(__file__),
        ),
        timeout=120.0,
    )
)

# Define the GitHub Dev Card Agent
github_card_agent = Agent(
    name="github_card_agent",
    description="An agent that generates developer cards based on GitHub profiles.",
    instruction="""
    You are a GitHub profile analyst and dev card generator. 
    When a user gives you a GitHub username, you ALWAYS follow this exact sequence: 
    1. Call 'scrape_github' with the username.
    2. Call 'analyze_profile' with the scraped result.
    3. Call 'generate_card_html' with the username, scraped data, and analysis.
    4. Call 'save_card' with the username and HTML.
    
    Never skip steps. Be enthusiastic about developers' work. 
    If the profile is private or doesn't exist, say so clearly.
    """,
    model="gemini-2.5-flash",
    tools=[mcp_tools]
)

def run_agent(username: str):
    """Entry point to run the agent logic."""
    return github_card_agent.run(f"Generate a dev card for user: {username}")
