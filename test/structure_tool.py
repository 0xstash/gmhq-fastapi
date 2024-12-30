import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.structures import Agent, Pipeline, Workflow
from griptape.drivers import LocalStructureRunDriver, OpenAiChatPromptDriver
from griptape.tasks import ToolkitTask, StructureRunTask
from griptape.tools import StructureRunTool, WebSearchTool
from griptape.loaders import WebLoader
from griptape.rules import Rule, Ruleset
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from dotenv import load_dotenv

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)


def joke_agent() -> Agent:
    return Agent(
        rules=[
            Rule(
                "You are an expert joke writer that always writes jokes in a pirate language.",
            )
        ]
    )


web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
structure_run_tool = StructureRunTool(
    description="Joke generator tool - Structure to invoke when a joke generation is needed",
    structure_run_driver=LocalStructureRunDriver(create_structure=joke_agent),
)

agent = Agent(tools=[structure_run_tool, web_search_tool])

agent.run(
    "Please find a recent news on Salesforce and create a joke around it to be able to tweet"
)
