import os
import sys
import logging
import json
import questionary
from rich.pretty import pprint
from openai import NOT_GIVEN
import schema

# Add the project root directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from griptape.configs.defaults_config import LoggingConfig
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent, Pipeline, Workflow
from pydantic import BaseModel
from rich.pretty import pprint

# tools
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)

from griptape.utils import StructureVisualizer
from griptape.configs import Defaults
from griptape.loaders import WebLoader
from griptape.tools import (
    WebSearchTool,
    WebScraperTool,
    PromptSummaryTool,
)
from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    GooglePromptDriver,
)
from griptape.utils import Chat, Stream
from griptape.tasks import PromptTask, ToolkitTask
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())


Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(
        model="gpt-4o", structured_output_strategy="native"
    ),
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

# Add questionary prompt for company website
company_website = questionary.text(
    "What is your company website?",
    validate=lambda text: True if len(text) > 0 else "Please enter the website",
).ask()


agent = Agent()

agent.add_task(
    PromptTask(
        output_schema=schema.Schema(
            {
                "company_info": {
                    "company_name": str,
                    "company_description": str,
                },
                "value_propositions": [
                    schema.Schema(
                        {
                            "problem": str,
                            "solution": str,
                            "benefits": str,
                            "target_audience": str,
                        }
                    )
                ],
                "summary": str,
            }
        ),
        input="""
        Using the provided company website, analyze the company and provide a detailed breakdown.
        
        Analyze the website and structure your response with the following information:
        
        1. Company Information:
           - Extract the official company name
           - Provide a clear, comprehensive description of what the company does
        
        2. For each major product/service, provide:
           - The specific problem it solves
           - How the solution works
           - Key benefits and advantages
           - Who it's designed for (target audience)
        
        3. Provide a brief summary that captures the company's overall value proposition
        
        Format the response as a JSON object with:
        - company_info: Object containing company_name and company_description
        - value_propositions: Array of objects, each with problem, solution, benefits, and target_audience
        - summary: A concise overview of the company's main value proposition
        
        Analyze: {{args[0]}}
        """,
        tools=[web_scraper_tool, web_search_tool],
    )
)

agent.run(company_website)
