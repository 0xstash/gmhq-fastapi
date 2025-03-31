import os
import sys
import json
import logging
from datetime import datetime
import questionary
from dotenv import load_dotenv

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(project_root)

from griptape.loaders import WebLoader
from griptape.configs.logging import JsonFormatter
from griptape.structures import Workflow
from griptape.tools import WebScraperTool, WebSearchTool
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from griptape.drivers import AnthropicPromptDriver, OpenAiChatPromptDriver
from griptape.tasks import PromptTask
from griptape.rules import Ruleset, Rule

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
user_info_path = os.path.join(project_root, "test", "data", "user_information.json")

with open(user_info_path, "r") as file:
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

# ---- Drivers ----

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    )
)

target_company = questionary.text("What is the target company?").ask()

identity_ruleset = Ruleset(
    name="Information about the identity of the email sender and his or her company",
    rules=[
        Rule(f"""
    Your identity is as follows: 
    - First name: {user_information_selected["first_name"]}
    - Last name: {user_information_selected["last_name"]}
    - Company name: {user_information_selected["company"]}
    - Company website: {user_information_selected["website"]}
    - Job title: {user_information_selected["title"]}
    - Product description: {user_information_selected["product_description"]}
    - Value props of the product and problems it solves: {user_information_selected["value_props"]}
    - {user_information_selected["first_name"]}'s calendar link to book a call: {user_information_selected["calendar_link"]}
    """)
    ],
)


research_task = PromptTask(
    """
    You are a business intelligence researcher working for {{my_company}} analyzing the target company to identify potential business challenges and opportunities.
Today's date is {{today}}
Research Focus:
1. Company Overview
- Core business model
- Recent strategic initiatives
- Market positioning

2. Key Areas of Investigation:
- recent news 
- Recent events
- Recent product launches
- Digital transformation efforts
- Technology investments
- Operational challenges
- Innovation gaps
- Hiring trends in critical roles
- Job postings

3. Research Methodology:
- Prioritize sources from last 12 months
- Use:
  * Company website
  * Press releases
  * LinkedIn
  * Recent news articles
  * Job postings

Output Requirements:
- 300-500 words
- Structured insights
- Actionable business intelligence
- List of verified sources

Specific Objectives:
- Identify unique business challenges
- Detect potential technology gaps
- Highlight areas for strategic improvement

Target Company: {{target_company}}

Provide 2-3 specific angles where value can be added.
    """,
    id="research_task",
    rulesets=[identity_ruleset],
    tools=[web_search_tool, web_scraper_tool],
    context={
        "today": datetime.now().strftime("%Y-%m-%d"),
        "my_company": user_information_selected["company"],
        "target_company": target_company,
    },
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini"),
)

summary_task = PromptTask(
    """
    You are a strategic advisor turning research into a razor-sharp business opportunity brief.

Brief Composition Rules:
- Use punchy, direct language
- Be specific, not generic
- Ground recommendations in evidence

Required Brief Structure:
1. Pain Point Diagnosis
- Identify 1-2 CRITICAL business challenges
- Link challenges to research findings

2. Solution Mapping
- Match {{my_company}}'s capabilities to identified challenges
- Highlight unique advantages

3. Tactical Recommendation
- Provide a SPECIFIC, implementable next step
- Sound like a trusted advisor

Tone: Confident, precise

Output: 
- Maximum 100 words
- Clear, bold recommendation
- Sound like a human expert

Target: {{target_company}}
Value Props: {{value_props}}
Research Findings: {{parents_output_text}}
    """,
    id="summary_task",
    rulesets=[identity_ruleset],
    context={
        "value_props": user_information_selected["value_props"],
        "today": datetime.now().strftime("%Y-%m-%d"),
        "my_company": user_information_selected["company"],
        "target_company": target_company,
    },
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-haiku-20241022"),
)

tasks = []
research_task.add_child(summary_task)

tasks.append(research_task)
tasks.append(summary_task)

workflow = Workflow(tasks=[*tasks])

# Run the workflow and get results
results = workflow.run()

# Create output directory if it doesn't exist
output_dir = os.path.join(project_root, "test", "data")
os.makedirs(output_dir, exist_ok=True)

# Save the results to a JSON file with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"research_results_{timestamp}.json")

# Get specific task outputs
output_data = {
    "timestamp": timestamp,
    "research_task": workflow.task_outputs["research_task"].to_dict()
    if "research_task" in workflow.task_outputs
    else None,
    "summary_task": workflow.task_outputs["summary_task"].to_dict()
    if "summary_task" in workflow.task_outputs
    else None,
}

# Save to file
with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Results saved to: {output_file}")
