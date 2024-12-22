import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from griptape.structures import Agent, Pipeline, Workflow
from griptape.configs import Defaults
from griptape.tools import PromptSummaryTool
from griptape.drivers import OpenAiChatPromptDriver
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.tools import DateTimeTool, WebScraperTool, WebSearchTool
from griptape.utils import Chat, Stream
from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver
from griptape.loaders import WebLoader
from griptape.events import (
    BaseEvent,
    TextChunkEvent,
    ActionChunkEvent,
    BaseActionsSubtaskEvent,
)

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)


agent = Agent(
    stream=True, tools=[web_search_tool, web_scraper_tool, PromptSummaryTool()]
)

for event in agent.run_stream(
    "could you compile a list of customers of Clay.com",
    event_types=[BaseActionsSubtaskEvent],
):  # All Events by default, can be omitted.
    print(f"Event type: {event}\n")
    # print(f"Actions taken: {event.actions}")
