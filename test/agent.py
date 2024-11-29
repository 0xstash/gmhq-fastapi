from dotenv import load_dotenv
from griptape.structures import Agent
from griptape.tools import WebScraperTool, WebSearchTool, DateTimeTool

load_dotenv()

agent = Agent(tools=[DateTimeTool()])

agent.run("What is the current date and time?")
