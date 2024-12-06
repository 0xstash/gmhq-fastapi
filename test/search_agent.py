import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from griptape.structures import Agent
from drivers.serper_web_search_driver import SerperWebSearchDriver
from griptape.configs import Defaults
from griptape.tools import (
    DateTimeTool,
    WebSearchTool,
    WebScraperTool,
    PromptSummaryTool,
)
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from dotenv import load_dotenv

load_dotenv()


Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
agent = Agent(tools=[web_search_tool, DateTimeTool()])

agent.run("What are some recent news from today in AI ?")
