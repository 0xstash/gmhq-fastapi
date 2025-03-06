import os
import sys
import logging
import json
import questionary
from rich.pretty import pprint
import schema
from rich import print as rprint
from rich import print_json
import requests
from schema import Schema, And, Use, Optional

# Add the project root directory to Python path
# Add the project root directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "test",
        "data",
    )
)
from griptape.configs.defaults_config import LoggingConfig
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent, Pipeline, Workflow

# tools
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from extension.tools.apollo.apollo_tool import ApolloClient

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
from griptape.drivers.prompt.openai import OpenAiChatPromptDriver
from griptape.drivers.prompt.anthropic import AnthropicPromptDriver
from griptape.drivers.prompt.google import GooglePromptDriver
from griptape.tasks import PromptTask
from griptape.rules import Ruleset, Rule
from datetime import datetime
import json

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())


Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
)

# Get the project root directory
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Use absolute path to open the file
with open(
    os.path.join(project_root, "test", "data", "user_information.json"), "r"
) as file:
    user_information = json.load(file)

company_choices = [
    f"{user['company']} - {user['first_name']} {user['last_name']}"
    for user in user_information
]

# Prompt user to select a company using questionary
selected_company = questionary.select(
    "What company would you like to analyze?", choices=company_choices
).ask()

# Get the selected company's information
selected_company_name = selected_company.split(" - ")[0]
user_information_selected = next(
    user for user in user_information if user["company"] == selected_company_name
)

# Get the accounts tracked monitoring list
with open(
    os.path.join(project_root, "test", "data", "accounts_tracked.json"), "r"
) as file:
    accounts_tracked = json.load(file)

# ---- Drivers ----
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True)
)

identity_ruleset = Ruleset(
    name="User identity guidelines and information",
    rules=[
        Rule(
            f"""
            Your identity is as follows:
            - First name: {user_information_selected["first_name"]}
            - Last name: {user_information_selected["last_name"]}
            - Company name: {user_information_selected["company"]}
            - Company website: {user_information_selected["website"]}
            - Job title: {user_information_selected["title"]}
            - The user lives in: {user_information_selected["location"]["city"]}, {user_information_selected["location"]["country"]}
            - Description of the product or service: {user_information_selected["product_description"]}
            - The problems solved for the customer: {user_information_selected["value_props"]}
            - Your booking calendar link as a call to action: {user_information_selected["calendar_link"]}

            Always be factual about these details in your generation. For example, do not generate things as if you are living somewhere else other than {user_information_selected["location"]["city"]}, {user_information_selected["location"]["country"]}

            """
        ),
    ],
)

tasks = []

for index, company in enumerate(accounts_tracked):
    rprint(
        f"[blue]Processing:[/blue] [yellow]{company['name']}[/yellow] and domain [green]{company['domain']}[/green]"
    )

    search_task = PromptTask(
        input="""
        Today's date is {{today_date}}.
        Who is the CEO of {{company_name}}?
        """,
        id=f"search_task_{index}",
        context={
            "company_name": company["name"],
            "company_domain": company["domain"],
            "today_date": datetime.now().strftime("%Y-%m-%d"),
        },
        tools=[
            WebSearchTool(
                web_search_driver=SerperWebSearchDriver(
                    api_key=os.getenv("SERPER_API_KEY"), num=50, date_range="m"
                )
            )
        ],
    )

    tasks.append(search_task)

workflow = Workflow(tasks=[*tasks])
print(StructureVisualizer(workflow).to_url())
