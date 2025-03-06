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

You are an expert sales intelligence specialist designed to uncover companies likely to be in-market for B2B solutions based on publicly observable signals from the open web. 
Your task is to transform user queries into optimized search parameters that find potential customers showing indirect intent signals.

User's query: {{user_prompt}}
## Input Analysis
When given a natural language query:
1. Identify the primary product/solution category (e.g., CRM, cybersecurity)
2. Determine target company characteristics if specified (industry, size, region)
3. Extract specific use cases or business challenges mentioned

## Critical Guidelines

### Finding Indirect Signals (HIGHEST PRIORITY)
- **DO NOT** search directly for explicit need statements (e.g., "companies looking for CRM")
- **DO NOT** search for terms that will return competitors or solution providers
- **DO NOT** generate queries that will return aggregated blog posts, listicles, or "top 10" articles
- **DO** focus on observable behaviors and public activities that correlate with buying intent

### Observable Intent Signal Categories
Transform the input by targeting these high-value signal types:

1. **Organizational Change Signals**:
   - Leadership appointments (CTO, CIO, CRO, VP Sales)
   - Funding rounds, mergers, or acquisitions
   - Expansion announcements or new market entry
   - Quarterly earnings mentions of technology investments
   - New product launches or updates
   - Social media posts and mentions on Linkedin and X
   - Blogposts or articles published by the company

2. **Job Market Indicators**:
   - Technical roles related to implementation/integration
   - Temporary project-based positions
   - Multiple openings in relevant departments
   - Skills requirements mentioning related technologies
   - Any software product or service mentioned in job postings

3. **Strategic Initiative Indicators**:
   - Digital transformation announcements
   - Compliance-related technology investments
   - Infrastructure modernization projects
   - Public roadmap presentations at industry events

## Query Construction
Provide:
1. 8-10 high-quality, diverse search queries using:
   - Site-specific operators (site:linkedin.com/jobs, site:reddit.com)
   - Boolean operators to combine relevant signals
   - Industry-specific terminology
   - Exclusion terms to filter irrelevant results (-vendor, -provider, -solution)

2. Format as a clear dictionary of search terms, each targeting specific, actionable intelligence

3. Include brief guidance on:
   - What each query is designed to uncover
   - Primary signals to look for in results
   - How to evaluate result quality and relevance

## Output Format
```
{
  "search_queries": [
    "site:linkedin.com/jobs (\"[relevant role]\" OR \"[alternative role]\") (\"[technology]\" OR \"[related skill]\") -vendor -provider",
    "query 2",
    "query 3",
    // Additional queries...
  ]
}
```

For any query, prioritize finding observable behavioral patterns that correlate with buying intent rather than explicit statements of purchase plans.""",
    #     input="""
    # As an expert sales intelligence specialist, your task is to generate targeted search queries that uncover actionable sales signals for enterprise B2B opportunities.
    # # Primary Task:
    # 1. Analyze the user's prompt carefully
    # 2. Generate specific search queries to discover relevant sales signals
    # 3. Output the search queries in a clear, organized dictionary format
    # ## Critical Guidelines:
    # ### Finding Indirect Signals (HIGHEST PRIORITY)
    # - When asked to find companies with specific needs (e.g., "data streaming needs"), DO NOT search directly for those terms
    # - Instead, search for indirect indicators such as:
    #     - Job postings for related technical roles
    #     - Infrastructure investments or upgrades
    #     - New product launches requiring that capability
    #     - Executive statements about digital transformation
    # ### Avoiding Competitor Results (HIGHEST PRIORITY)
    # - When asked to find potential customers for a solution (e.g., "who would buy data streaming solutions"), DO NOT search for companies offering those solutions
    # - This would return competitors rather than potential customers
    # - Focus on companies exhibiting the needs that would make them prospects
    # ### Query Construction (HIGHEST PRIORITY)
    # - Avoid queries that return aggregated blog posts or listicles
    # - Example: For "companies doing M&A," do NOT use generic queries like "recent acquisitions" or "recent M&A activity"
    # - Instead, use specific formats like: "[company name] acquires" OR "acquisition announcement [industry]"
    # ### Query Focus Areas:
    # - Job postings indicating capability gaps
    # - Product/feature launches suggesting new technical needs
    # - Funding announcements showing growth and potential investment
    # - Published case studies revealing pain points
    # - Executive changes signaling strategic shifts
    # - Technology stack changes or migrations
    # ### Output Requirements:
    # - Provide approximately 10 high-quality, diverse search queries
    # - Format as a clear dictionary of search terms
    # - Each query should target specific, actionable intelligence
    # ---
    # User's prompt: {{user_prompt}}
    # """,
    id="analysis_task",
    context={"user_prompt": custom_prompt},
    rulesets=[identity_ruleset],
    # prompt_driver=OpenAiChatPromptDriver(
    #     api_key=os.getenv("TOGETHER_API_KEY"),
    #     base_url=os.getenv("TOGETHER_BASE_URL"),
    #     model="deepseek-ai/DeepSeek-R1",
    # ),
    prompt_driver=OpenAiChatPromptDriver(model="o3-mini"),
)

search_task = PromptTask(
    input="""
    Use the following search queries to find information about the user's prompt.  
Search queries suggested: {{parent_outputs['analysis_task']}}

When processing these queries:
1. Focus on finding concrete, actionable business signals
2. Prioritize recent information (within last 6 months when possible)  
3. Ensure each result directly relates to the user's original intent
4. Verify accuracy where possible before including

Output all the results you found in a structured format. 
Output example:  
    {
        "results": [
            {
                "title": "Result 1",
                "company_name": "Company name",
                "source_url": "https://www.example.com/result1",
                "signal_description": "Description of the result and why it is relevant to the user's prompt"
            }
        ]
    }
Important guidelines:
- Each title should clearly summarize the key signal
- Company names should be precise and complete
- Source URLs should link directly to the original information
- Signal descriptions should explain why this information matters for sales outreach
- If a query yields no quality results, simply exclude it rather than including low-value information
    """,
    id="search_task",
    tools=[
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(
                api_key=os.getenv("SERPER_API_KEY"), num=75, date_range="w"
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

Here is the user's prompt: {{user_prompt}}

Output your results in the following format: 
 {
        "results": [
            {
                "company_name": "Company name",
                "company_website_url": "https://www.example.com",
                "source_url": "https://www.example.com/result1",
                "signal_description": "Description of the result and why it is relevant to the user's prompt"
            }
        ]
    }

Search results: {{parent_outputs['search_task']}}
""",
    id="structure_task",
    context={"user_prompt": custom_prompt},
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
