import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.structures import Agent, Pipeline, Workflow
from griptape.tools import WebScraperTool, WebSearchTool, PromptSummaryTool
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.rules import Rule, Ruleset
from dotenv import load_dotenv

load_dotenv()

agent = Agent("Your task is to create a", tools=[PromptSummaryTool()])
