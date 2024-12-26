from dotenv import load_dotenv
import os
import logging
import uuid
from typing import Optional
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver

from griptape.utils import Chat
from griptape.loaders import WebLoader
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import (
    DateTimeTool,
    BaseTool,
    VectorStoreTool,
    PromptSummaryTool,
    WebSearchTool,
    WebScraperTool,
)
from griptape.drivers import GriptapeCloudVectorStoreDriver
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.drivers import GriptapeCloudConversationMemoryDriver
from griptape.structures.structure import ConversationMemory
from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    BaseActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)

from rich import print as rprint, print_json

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)
Defaults.drivers_config.conversation_memory_driver = (
    GriptapeCloudConversationMemoryDriver(
        api_key=os.getenv("GRIPTAPE_CLOUD_API_KEY"),
        thread_id="bd624074-f8e1-406e-bc2c-d3c2907b65cf",
    )
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

vector_store_driver = GriptapeCloudVectorStoreDriver(
    api_key=os.getenv("GRIPTAPE_CLOUD_API_KEY"),
    knowledge_base_id=os.getenv("GRIPTAPE_CLOUD_FINANCIALS_KB_ID"),
)

vector_db = VectorStoreTool(
    description="Contains information on financials of companies",
    vector_store_driver=vector_store_driver,
    off_prompt=True,
)


agent = Agent(
    tools=[vector_db, PromptSummaryTool(), web_search_tool, web_scraper_tool],
)

result = agent.run(
    "Tell me about the hardware business of Oracle please. Particularly the margins. Also please find out the latest product launch or annoucement they have"
)
