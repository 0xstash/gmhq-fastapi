import os
import sys
import logging
import json

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs.defaults_config import LoggingConfig
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
    DateTimeTool,
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
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.tasks import PromptTask, ToolkitTask
from datetime import datetime

from dotenv import load_dotenv

# Load user information
with open("test/data/user_information.json", "r") as file:
    user_information_godmode = json.load(file)[0]  # Get the first user's information


load_dotenv()

# Get and print today's date
current_date = datetime.now().strftime("%d %B %Y")
print(f"Today's date is: {current_date}")


# Defaults.drivers_config = OpenAiDriversConfig(
#     prompt_driver=OpenAiChatPromptDriver(model="gpt-4o", stream=True)
# )

Defaults.drivers_config = AnthropicDriversConfig(
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-sonnet-20241022", stream=True)
)

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())


def on_event(event: BaseEvent) -> None:
    if isinstance(event, (StartActionsSubtaskEvent, FinishActionsSubtaskEvent)):
        # Create the log entry for subtask actions
        log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        log_entry += f"Event Class: {event.__class__.__name__}\n"
        log_entry += f"Task ID: {event.task_id}\n"
        log_entry += f"Timestamp: {event.timestamp}\n"

        log_entry += "\nSubtask Actions:\n"
        for action in event.subtask_actions:
            log_entry += f"Tool Name: {action.get('name')}\n"
            log_entry += f"Tool Path: {action.get('path')}\n"
            log_entry += f"Tool Input: {action.get('input')}\n"
            log_entry += f"Tool Output: {action.get('output')}\n"
            log_entry += "---\n"

        log_entry += "=" * 80 + "\n"  # Separator between entries

        # Read existing content
        log_file = "test/data/event_logs.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        existing_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                existing_content = f.read()

        # Write new content at the top
        with open(log_file, "w") as f:
            f.write(log_entry + existing_content)

        # Also print to console
        print(log_entry)

    elif isinstance(event, FinishPromptEvent):  # Handle prompt completion
        log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        log_entry += f"Event Class: {event.__class__.__name__}\n"
        log_entry += f"Task ID: {event.id}\n"
        log_entry += f"Timestamp: {event.timestamp}\n"
        log_entry += f"\nFinal Task Output:\n{event.result}\n"
        log_entry += "=" * 80 + "\n"  # Separator between entries

        # Write to file
        log_file = "test/data/event_logs.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        existing_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                existing_content = f.read()

        # Write new content at the top
        with open(log_file, "w") as f:
            f.write(log_entry + existing_content)

        # Also print to console
        print(log_entry)


EventBus.add_event_listeners(
    [
        EventListener(
            on_event,
            event_types=[
                StartTaskEvent,
                FinishTaskEvent,
                StartActionsSubtaskEvent,
                FinishActionsSubtaskEvent,
                StartPromptEvent,
                FinishPromptEvent,
            ],
        )
    ]
)

news_web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(
        api_key=os.getenv("SERPER_API_KEY"), type="news", date_range="d"
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
    context={"website": user_information_godmode["website"]},
    id="icp_task",
)

signal_search_task = PromptTask(
    """
You are tasked with generating search queries for Google web search based on a B2B company's ideal customer profile and solution. The purpose of these queries is to find relevant news, insights, or web data that could indicate potential pain points the company might be solving for. It's crucial that the reasoning and relevance of the signals are rational and make sense, without forced logic.

First, carefully review the ideal customer profile and the company's solution:

Your task is to create search queries that will help identify potential customers who may be experiencing challenges related to the company's solution. These queries should be designed to uncover signals such as:

1. Social media engagement and content
2. Job changes
3. Funding announcements
4. Product launches
5. Partnership announcements
6. Any indication that a company or individual is struggling with issues the company's solution addresses

When creating your search queries, follow these guidelines:

1. Ensure each query is directly related to the ideal customer profile and the company's solution
2. Use industry-specific terminology when appropriate
3. Combine relevant keywords to narrow down results
4. Utilize Boolean operators (AND, OR, NOT) to refine searches
5. Consider including company names, job titles, or industry verticals from the ideal customer profile

Here are two examples of well-constructed search queries with relevance explanations:

1. "Chief Financial Officer" AND ("financial reporting challenges" OR "compliance issues") AND ("software solution" OR "automation") -job
   Relevance: This query targets high-level decision-makers in finance who may be experiencing difficulties that the company's solution could address, while excluding job postings.

2. "Series B funding" AND ("supply chain management" OR "logistics optimization") AND ("inefficiencies" OR "bottlenecks") site:techcrunch.com
   Relevance: This query focuses on recently funded companies in the supply chain sector that might be looking to improve their operations, using a reputable tech news source.

Remember, the goal is to create queries that will lead to meaningful signals of potential customer need, always keeping in mind the ideal customer profile and the company's solution.   

Value props of {{company_name}}: {{value_props}}
Ideal customer profile: {{parent_outputs['icp_task']}}
    """,
    tools=[
        web_scraper_tool,
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(
                api_key=os.getenv("SERPER_API_KEY"), date_range="d"
            )
        ),
        PromptSummaryTool(),
    ],
    context={
        "company_name": user_information_godmode["company"],
        "value_props": user_information_godmode["value_props"],
    },
    id="signal_search_task",
)

news_search_task = PromptTask(
    """
Based on the following detailed definition of ideal customer profile for {{company_name}}
""",
    tools=[
        web_scraper_tool,
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(
                api_key=os.getenv("SERPER_API_KEY"), type="news", date_range="d"
            )
        ),
        PromptSummaryTool(),
    ],
    context={"company_name": user_information_godmode["company"]},
    id="news_search_task",
)

tasks = []
tasks.append(icp_task)
tasks.append(signal_search_task)

icp_task.add_child(signal_search_task)

workflow = Workflow(tasks=[*tasks])

print(StructureVisualizer(workflow).to_url())

workflow.run()
