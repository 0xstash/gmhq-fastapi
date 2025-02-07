import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.structures import Agent, Pipeline
from griptape.tasks import PromptTask
from griptape.loaders import WebLoader
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.tools import (
    WebScraperTool,
    WebSearchTool,
    DateTimeTool,
    PromptSummaryTool,
)

load_dotenv()

with open("test/data/user_information.json", "r") as file:
    user_information_godmode = json.load(file)[0]  # Get the first user's information

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)

icp_task = PromptTask(
    """
You are tasked with generating a detailed ideal customer profile based on the website content of a B2B product. Your goal is to extract relevant information and create a comprehensive profile that includes key attributes of the ideal customer. The profile should be based solely on the information provided in the website content and should focus on details that can be verified or found on the open web.

Carefully read through the website content and extract information relevant to the following attributes of an ideal customer profile:

1. Company size/revenue range
2. Industry verticals
3. Technology stack
4. Business challenges/pain points
5. Buying triggers/signals
6. Decision maker profiles

For each attribute, provide your reasoning based on the website content before stating the attribute. This will help justify your conclusions.

After analyzing the content, compile your findings into a structured ideal customer profile. Use the following format for your response:

<ideal_customer_profile>
<company_size_revenue>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[State the company size/revenue range]
</attribute>
</company_size_revenue>

<industry_verticals>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[List the industry verticals]
</attribute>
</industry_verticals>

<technology_stack>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[Describe the technology stack]
</attribute>
</technology_stack>

<business_challenges>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[List the business challenges/pain points]
</attribute>
</business_challenges>

<buying_triggers>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[Describe the buying triggers/signals]
</attribute>
</buying_triggers>

<decision_makers>
<reasoning>
[Provide your reasoning here]
</reasoning>
<attribute>
[Describe the decision maker profiles]
</attribute>
</decision_makers>
</ideal_customer_profile>

Remember to focus on information that can be found or verified on the open web. If you cannot find sufficient information for any attribute, state that it's not clearly defined in the website content and provide a reasonable assumption based on the available information.

Ensure that your analysis is thorough and that you provide clear reasoning for each attribute in the ideal customer profile. Your goal is to create a comprehensive and accurate profile based solely on the provided website content.

Website: {{website}}
    """,
    tools=[
        web_scraper_tool,
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
        ),
    ],
    context={"website": "terabee.com"},
    id="icp_task",
    prompt_driver=AnthropicPromptDriver(
        model="claude-3-5-sonnet-20241022", stream=True
    ),
)

agent = Agent()

agent.add_task(icp_task)

agent.run()
