import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.structures import Workflow, Agent
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.structures import Agent, Pipeline, Workflow
from griptape.tools import WebScraperTool, WebSearchTool, PromptSummaryTool
from griptape.loaders import WebLoader
from griptape.tasks import PromptTask, ToolkitTask
from dotenv import load_dotenv

load_dotenv()

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

analyse_task = PromptTask(
    """
Based on the following query from the user, extract and understand what kind of people we should be searching for. 
The type of these target customers should be specific, clear. When done an online research on social media, forums and news, it should always yield results realistically. 
Output a list of keywords to google. It cannot be as obvious as the query but it should be a list of keywords that are relevant to the query or the results should have a logical inferential relationship to the query.
For example if the user's query is "Find me people who are looking to sell their businesses in software", then you would look for quotes in social media, reddit and other places for businesses who have a bad financial situation or posts where someone wrote that they are looking to sell their business. 

Query: {{args[0]}}
    """,
    id="task_1",
)

search_task = ToolkitTask(
    """
Based on the following keywords, search the web and find people and/or companies. 
We are looking for companies or people who have a particular need or a pain point. 
Never aggregate related platforms or forums or news etc as relevant as these are merely sources. 
The results should be structured and formatted as the following:

1. Company or person name
1a. Your reasoning as to why you picked this against user's query
1b. Reference links

Keywords: {{parents_output_text}}
User's query: {{args[0]}}
""",
    id="task_2",
    tools=[web_search_tool, web_scraper_tool, PromptSummaryTool()],
)

tasks = []
tasks.append(analyse_task)
tasks.append(search_task)
analyse_task.add_child(search_task)

workflow = Workflow(tasks=[*tasks])


query = "Find me people who are looking to sell their businesses in software"
workflow.run(query)
