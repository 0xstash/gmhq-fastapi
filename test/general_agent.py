import os
import sys
from rich import print as rprint
from rich import print_json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.tools import DateTimeTool, WebSearchTool, WebScraperTool
from dotenv import load_dotenv
from artifact.artifact_agent import ArtifactAgent
from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver
from griptape.utils import Chat
from griptape.rules import Rule, Ruleset
from griptape.loaders import WebLoader


load_dotenv()

# Configure the OpenAI driver
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)
web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY")),
    )
)
agent = ArtifactAgent(
    tools=[DateTimeTool(), web_search_tool, web_scraper_tool], stream=True
)

Chat(agent).start()
