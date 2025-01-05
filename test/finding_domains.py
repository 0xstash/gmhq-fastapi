import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.structures import Agent, Pipeline, Workflow
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.tools import (
    WebSearchTool,
    DateTimeTool,
    WebScraperTool,
    PromptSummaryTool,
)
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.loaders import WebLoader
from griptape.rules import Rule, Ruleset
from griptape.tasks import ToolkitTask, PromptTask

from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

# Read companies from CSV file
df = pd.read_csv("test/data/M Test.csv")
companies = df["Company"].unique().tolist()[1:100]  # Take companies 4-20
test_companies = ["GodmodeHQ", "Incident"]

tasks = []

for company in companies:
    domain_finder_task = ToolkitTask(
        "Your task is to find the website URL of the following company: {{company_name}}. If there is no information just output 'None'.",
        context={"company_name": company},
        tools=[web_search_tool],
        id=f"DOMAIN_TASK_{company}",
        rules=[Rule("Always output only the website URL and nothing else")],
        max_subtasks=5,
    )
    tasks.append(domain_finder_task)

workflow = Workflow(tasks=[*tasks])
workflow.run()

# Get all task outputs as a dictionary
task_outputs = workflow.task_outputs

# Create a dictionary to store company-website pairs
website_dict = {}

# Iterate through task outputs and store in dictionary
for task_id, output in task_outputs.items():
    # Extract company name from task_id (remove "DOMAIN_TASK_" prefix)
    company = task_id.replace("DOMAIN_TASK_", "")
    website_dict[company] = str(output)

# Read the original CSV
df = pd.read_csv("test/data/M Test.csv")

# Add website column from the dictionary
df["Website"] = df["Company"].map(website_dict)

# Save the updated dataframe back to CSV
df.to_csv("test/data/M Test.csv", index=False)

print("CSV file has been updated with website information.")
