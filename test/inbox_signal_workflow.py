import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from griptape.structures import Agent
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.configs import Defaults
from griptape.tasks import ToolkitTask
from griptape.loaders import WebLoader
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

system_prompt_template = """
You are an expert salesperson. Your task lies in scouring the web to find signals, news and related up-to-date recent information that our company can use. 
The information you find must be actionable and relevant. We will use this information for outreach and relationship building with our prospects. 
Before searching the internet, plan and think about the keywords you will use. Always try to avoid directories or SEO aimed articles.

Here is information on our company. 

GodmodeHQ is building the AI virtual employees for sales that can automate sales tasks like sourcing, account research, enrichment and outreach. GMHQ can help you acquire more customers in a much more efficient way by freeing up time for your sales team. 

GMHQ will source leads based on hiring, funding and tech stack data, do account research, write outreach emails and present them for your review. 

Sales organizations are bogged down with too slow and too manual tasks. With AI, we can automate the first 90% effectively replacing the need for data collection and analysis work so you can work your magic in the last mile. 

GMHQ centralises sourcing of leads, account research and outreach generation so you can work faster with higher quality leads in your outbound. 
"""

Defaults.drivers_config = OpenAiDriversConfig(OpenAiChatPromptDriver(model="gpt-4o"))

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)

agent = Agent()
agent.add_task(
    ToolkitTask(
        generate_system_template=lambda task: f"{system_prompt_template}",
        tools=[web_search_tool, web_scraper_tool, PromptSummaryTool()],
    )
)

agent.run(
    "Find me some software companies operating in the real estate space. It would be good if they have AI feautres "
)
