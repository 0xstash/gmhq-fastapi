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
            - First name: {user_information_selected['first_name']}
            - Last name: {user_information_selected['last_name']}
            - Company name: {user_information_selected['company']}
            - Company website: {user_information_selected['website']}
            - Job title: {user_information_selected['title']}
            - The user lives in: {user_information_selected['location']['city']}, {user_information_selected['location']['country']}
            - Description of the product or service: {user_information_selected['product_description']}
            - The problems solved for the customer: {user_information_selected['value_props']}
            - Your booking calendar link as a call to action: {user_information_selected['calendar_link']}

            Always be factual about these details in your generation. For example, do not generate things as if you are living somewhere else other than {user_information_selected['location']['city']}, {user_information_selected['location']['country']}

            """
        ),
    ],
)

# Prompt user for their custom prompt
custom_prompt = questionary.text(
    "What is your prompt?", multiline=True, instruction="Press Esc+Enter to submit"
).ask()

if custom_prompt is None:
    raise ValueError("Prompt cannot be empty")

rprint(f"[green]Prompt by the user:[/green] {custom_prompt}")

# Define the schema for a single result item
result_item_schema = Schema(
    {
        "company_name": And(str, len),  # Non-empty string
        "company_website_url": And(
            str, lambda s: s.startswith(("http://", "https://"))
        ),  # Valid URL
        "source_url": And(
            str, lambda s: s.startswith(("http://", "https://"))
        ),  # Valid URL
        "signal_description": And(str, len),  # Non-empty string
    }
)

# Define the main schema
structure_schema = Schema(
    {
        "results": [result_item_schema]  # List of result items
    }
)

analysis_task = PromptTask(
    input="""
You are an expert sales agent for enterprise B2B sales to generate search queries to find signals. Here are guidelines for your task:  

Tasks step by step: 
1. Analyse the prompt below. 
2. Based on the prompt, identify key search queries that will help you find the most relevant information. The queries will be used in Google search to find information. 
3. Output the search queries in a dictionary.

Rules: 
- The queries should be specific and to the point. They are likely to be about the following things: 
    - Job postings
    - Product or feature launches
    - Funding rounds and news
    - Case studies published
    - Recent hiring news or executive changes and job changes
    - Anything else that is relevant to the prompt
- Ideally 10 search queries are enough. 
- If a user prompts something like "Find me companies who have data streaming needs", recognise that this need cannot be identified by just searching for "data streaming". You have to search for related things like if they are hiring for data streaming related roles or they are launching a data heavy product. THINK VERY HARD ON QUERIES LIKE THIS. 
- The most important factor are the following: 
    - The queries should not return aggregated blogpost results. For example, if prompt is "Looking for companies who are doing M&A", the query should not be "recent acquistions" or "recent M&A activity". This will return aggregated blogpost results. This example applies to all prompts and parallels you can draw
    

Example output:

{
    "search_queries": [
        "search query 1",
        "search query 2",
        "search query 3"
    ]
}

User's prompt: {{user_prompt}}
    
""",
    id="analysis_task",
    context={"user_prompt": custom_prompt},
    rulesets=[identity_ruleset],
)

search_task = PromptTask(
    input="""
    Use the following search queries to find information about the user's prompt.  
    Search queries suggested: {{parent_outputs['analysis_task']}}

    Output all the results you found in a structured format. 
    Output example: 
    {
        "results": [
            {
                "title": "Result 1",
                "company_name": "Company name",
                "source_url": "https://www.example.com/result1",
                "signal_description": "Description of the result"
            }
        ]
    }
    """,
    id="search_task",
    tools=[
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(
                api_key=os.getenv("SERPER_API_KEY"), num=50, date_range="w"
            )
        )
    ],
    max_subtasks=10,
)

structure_task = PromptTask(
    input="""
Analyse the following links and descriptions based on the following guide: 
1. The query should be related to user's prompt in that it should be actionable to reach out to the target company. If it is not, discard it. 
2. Find the target company's website URL (homepage)
3. Each result should belong to a seperate company in that the results are unique by the company. 
4. One signal per company can be generated. 
5. DEFINITELY DISCARD SEO LIKE ARTICLES AND OTHER NON-ACTIONABLE SIGNALS. ONLY RESULTS THAT ARE DIRECTLY LINKED TO THE TARGET COMPANY CAN BE CONSIDERED. 

Output your results in the following format: 
 {
        "results": [
            {
                "company_name": "Company name",
                "company_website_url": "https://www.example.com",
                "source_url": "https://www.example.com/result1",
                "signal_description": "Description of the result"
            }
        ]
    }

Search results: {{parent_outputs['search_task']}}
""",
    id="structure_task",
    tools=[web_search_tool],
    output_schema=structure_schema,
    max_subtasks=10,
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o"),
)

tasks = []
tasks.append(analysis_task)
tasks.append(search_task)
tasks.append(structure_task)
analysis_task.add_child(search_task)
search_task.add_child(structure_task)

workflow = Workflow(tasks=[*tasks])
print(StructureVisualizer(workflow).to_url())

workflow.run()

# Initialize output data structure
output_data = {
    "analysis_timestamp": datetime.now().isoformat(),
    "user_company": user_information_selected["company"],
    "user_prompt": custom_prompt,
    "analysis_results": {},
}

# Process all task results
for task in workflow.tasks:
    task_output = task.output.value if task.output else None
    output_data["analysis_results"][task.id] = task_output

    # Print task results to console
    rprint(f"[blue]Task id:[/blue] {task.id}")
    rprint(f"[green]Task output:[/green]")
    print_json(data=task_output)
    print("-" * 80)

# Save results to a file with timestamp
output_file = os.path.join(
    os.path.dirname(__file__),
    f"signals_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
)

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

# Count how many signals were found
if "structure_task" in output_data["analysis_results"]:
    signals_count = len(
        output_data["analysis_results"]["structure_task"].get("results", [])
    )
    rprint(f"\n[green]Analysis results saved to: {output_file}[/green]")
    rprint(f"[yellow]Found {signals_count} signals based on your search query[/yellow]")
