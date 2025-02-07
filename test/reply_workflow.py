import os
import sys
import logging
import json
from questionary import text, select
import questionary
from rich.pretty import pprint
from openai import NOT_GIVEN
import schema

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs.defaults_config import LoggingConfig
from griptape.rules import Rule, Ruleset
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent, Pipeline, Workflow
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.utils import StructureVisualizer
from griptape.configs import Defaults
from griptape.tasks import ToolkitTask
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
from griptape.tasks import PromptTask, ToolkitTask
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


Defaults.drivers_config = AnthropicDriversConfig(
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-sonnet-20240620")
)

reply_text = """

Hi Mert
 
Thanks for your email.
 
Forgive me If I am sceptical, but it sounds too good to be true, and in my experience such things usually are.
 
We have a very specific target market, before I commit to going any further I will present you with what I require and you let me know if you think your system can help.
 
I am interested if your system can handle “lead sourcing, account research” only, I am not interested in a “personal outreach” component.
 
Furthermore;
 
We have very specific prospect parameters, being the following;
 
Law firms -
In the following states only:
 Illinois
California
Florida
Texas
Indiana
Maryland
Florida
Number of attorneys in firm
 5 or more
Areas of practice:
 A combination of two or more of the following practice areas - Contract Law, Collections, Lemon Law, Personal Injury, Labor & employment, eviction, landlord/tennant, unlawful detainer
Contact Titles:
 Managing Partner / Owner/Practice Manager / Librarian / Knowledge Manager / Accountant/bookeeper
 
Case Management System
 
Clio
Mycase
Neos
 
Point #5 is not a deal breaker, but a nice-to-have.
 
Lastly, I’m not interested in a system that has a lot of bells & whistles that we won’t use (and don’t want to be sold onto these features either)
 
Let me know your thoughts please?
 
Regards
 
Brendan
"""

with open("test/data/user_information.json", "r") as file:
    user_information = json.load(file)

# Create company choices for selection
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


# agent.add_task(
#     ToolsTask(
#         generate_system_template=lambda task: f"{system_prompt_template}",
#         tools=[web_search_tool, workflow_structure_run_tool],
#     )
# )

agent = Agent()

identity_ruleset = Ruleset(
    name="Identity of the user",
    rules=[
        Rule(
            f"""
            Your identity is as follows
            - First name: {user_information_selected['first_name']}
            - Last name: {user_information_selected['last_name']} 
            - Company name: {user_information_selected['company']}
            - Company website: {user_information_selected['website']}
            - Job title: {user_information_selected['title']}
            - Your calendar link to book a call: {user_information_selected['calendar_link']}
        """
        ),
        Rule(
            f"""The value propositions, ideal customer profile and product description of {user_information_selected['company']} are below: 
            Value props: {user_information_selected['value_props']}
            Ideal customer profile: {user_information_selected['ideal_customer_profile']}
            Product description: {user_information_selected['product_description']}
            """
        ),
    ],
)

agent.add_task(
    PromptTask(
        input="""
        Your task is to produce a reply to the following email. You have received this email after sending a cold outreach email to the prospect. 
        The email should be human-readable, logical, and focused on solving the recipient's pain point. 
        Your output should only be the message. 

        You have to adhere to the following requirements and instructions: 
        1. Writing style and tone:
        - Use short and casual sentences
        - Keep the overall email concise (aim for 4-5 sentences)
        - Be friendly but professional
        - Use 5th grade language and always the simplest word for each term
        - Include a line break after each sentence
        - Write in a conversational tone

        2. Content requirements: 
        - Reply to the response received in a clear and explanatory way. 
        - if the prospect asked a question and you don't know the answer, make it a vague answer. 
        - Your goal is to land a live meeting with the prospect
        - Send over the calendar link to book a call if the calendar link exists.

        Details of the prospect: {{prospect_name}} from {{prospect_company}}
        Response received from {{prospect_name}}: {{reply_received}}
        """,
        context={
            "prospect_name": "Brendan Smart",
            "prospect_company": "Infotrack",
            "reply_received": reply_text,
        },
        rulesets=[identity_ruleset],
    )
)

agent.run()
