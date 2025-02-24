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

# Add the project root directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

# Load user information
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

rprint(
    f"Selected company: {user_information_selected['company']} with the website {user_information_selected['website']}"
)

# Prompt for website verification
customer_website = questionary.text(
    "Input an example company website:",
    validate=lambda text: True if len(text) > 0 else "Website cannot be empty",
).ask()

rprint(f"\nWebsite to analyze: {customer_website}")

# Prompt for custom analysis prompt
analysis_prompt = questionary.text(
    "What would you like to analyze about this company? (Enter a single prompt):",
    validate=lambda text: True if len(text) > 0 else "Prompt cannot be empty",
).ask()

rprint("\nStarting analysis...")
rprint(f"Target website: {customer_website}")
rprint(f"Analysis prompt: {analysis_prompt}")

# Initialize drivers
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

# Initialize tools
web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
)

# Find similar companies
rprint("\nFinding similar companies...")
url = "https://api.companyenrich.com/companies/similar"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {os.getenv('COMPANYENRICH_API_KEY')}",
}
payload = {"domain": customer_website, "page": 1, "pageSize": 5}

# Initialize output data structure
output_data = {
    "analysis_timestamp": datetime.now().isoformat(),
    "target_company": customer_website,
    "analysis_prompt": analysis_prompt,
    "similar_companies": [],
    "task_results": [],
}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    similar_companies = response.json()

    # Store similar companies in output data
    output_data["similar_companies"] = similar_companies.get("items", [])

    # Option 1: Print the entire similar_companies JSON
    print_json(data=similar_companies)

    # Option 2: Print specific company data
    for company in similar_companies.get("items", []):
        print_json(data=company)
        rprint("-" * 80)
except requests.exceptions.RequestException as e:
    rprint(f"[red]Error finding similar companies: {str(e)}[/red]")
    output_data["similar_companies_error"] = str(e)

tasks = []

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

            Always be factual and accurate about these details in your generation. 

            """
        ),
    ],
)

for index, company in enumerate(similar_companies.get("items", [])):
    rprint(f"Company {index + 1}:")
    rprint(f"Domain: {company.get('domain', 'N/A')}")
    rprint(f"Revenue: {company.get('revenue', 'N/A')}")
    rprint(f"Employees: {company.get('employees', 'N/A')}")
    rprint(f"Description: {company.get('description', 'N/A')}")
    socials = company.get("socials", {})
    if socials:
        if socials.get("linkedin_url"):
            rprint(f"LinkedIn: {socials['linkedin_url']}")
        if socials.get("twitter_url"):
            rprint(f"Twitter: {socials['twitter_url']}")
        if socials.get("facebook_url"):
            rprint(f"Facebook: {socials['facebook_url']}")
        if socials.get("instagram_url"):
            rprint(f"Instagram: {socials['instagram_url']}")
        if socials.get("youtube_url"):
            rprint(f"YouTube: {socials['youtube_url']}")
    rprint("-" * 80)

    search_task = PromptTask(
        """
        You are an expert sales and marketing analyst. You specialise in finding signals that can help you identify the best companies to sell to.

        First use se web search and web scraping to find information about the company. Here is a list of signals you can explicitly look for: 
        Signals: 
        - Funding rounds
        - Hiring data like if they started hiring recently
        - Recent hiring on the C-suite
        - Product launches
        - Reviews on the company
        - News articles about the company
        - Any other signals that you think are relevant
        
        Lastly, output your findings in bullet points. Summarise each point with the following sub bullets:
        - Signal
        - Summary of the signal
        - Link to the source in markdown format like [Source](https://www.google.com)
        
        This task will run on daily news 
        It might be the case that there is no related information to the company. In this case, just output "None".

        Here is information and data about the company:
        Website: {{company_name}}
        Company website: {{company_domain}}
        Company Linkedin URL: {{linkedin_url}}

        """,
        id=f"search_task_{index}",
        context={
            "company_name": company.get("name", "N/A"),
            "company_domain": company.get("domain", "N/A"),
            "company_description": company.get("description", "N/A"),
            "company_revenue": company.get("revenue", "N/A"),
            "company_employees": company.get("employees", "N/A"),
            "linkedin_url": company.get("socials", {}).get("linkedin_url", "N/A"),
        },
        tools=[web_search_tool, web_scraper_tool],
        max_subtasks=25,
    )

    analysis_task = PromptTask(
        """
        You will get a list of signals and summaries relating to a company. Your job is to relate to the signals and understand a potential pain point about the target company. 
        The potential pain point should be something that the target company is facing that we can help them solve.
        Your output should be the following format: 
        - Signal and pain point
        - Sources: Source 1 in markdown format like [Source 1](https://www.google.com), Source 2 in markdown format like [Source 2](https://www.google.com)
        - Reasoning: Your explanation of why this is a pain point and how we can help solve it

        Here are some tips and guidelines: 
        - The pain point is mainly something that we will later use to personalise our outreach to the target company. This means that you can use most signals to find a pain point or personalisation aspect. 
        - If there is no clear pain point, just output "None" and nothing else.

        ---
        Information about the target company:
        Website: {{company_name}}
        Company website: {{company_domain}}
        Company Linkedin URL: {{linkedin_url}}
        Signals found: \n{{parents_output_text}}
        """,
        id=f"analysis_task_{index}",
        output_schema=schema.Schema(
            {
                "signal_analysis": schema.Schema(
                    {
                        "signal_and_pain_point": str,
                        "sources": [str],  # List of markdown formatted source links
                        "reasoning": str,
                    },
                    required=True,
                )
            }
        ),
        context={
            "company_name": company.get("name", "N/A"),
            "company_domain": company.get("domain", "N/A"),
            "company_description": company.get("description", "N/A"),
            "company_revenue": company.get("revenue", "N/A"),
            "company_employees": company.get("employees", "N/A"),
            "linkedin_url": company.get("socials", {}).get("linkedin_url", "N/A"),
        },
        rulesets=[identity_ruleset],
    )

    tasks.append(search_task)
    tasks.append(analysis_task)

    search_task.add_child(analysis_task)


workflow = Workflow(tasks=[*tasks])

workflow.run()

for task in workflow.tasks:
    task_output = task.output.value if task.output else None

    # Handle different task types and their outputs
    if task.id.startswith("search_task_"):
        output_data["task_results"].append(
            {"task_id": task.id, "task_type": "search", "output": task_output}
        )
    elif task.id.startswith("analysis_task_"):
        # Handle the schema-based output for analysis tasks
        if (
            task_output
            and isinstance(task_output, dict)
            and "signal_analysis" in task_output
        ):
            output_data["task_results"].append(
                {
                    "task_id": task.id,
                    "task_type": "analysis",
                    "signal_and_pain_point": task_output["signal_analysis"][
                        "signal_and_pain_point"
                    ],
                    "sources": task_output["signal_analysis"]["sources"],
                    "reasoning": task_output["signal_analysis"]["reasoning"],
                }
            )
        else:
            output_data["task_results"].append(
                {"task_id": task.id, "task_type": "analysis", "output": "None"}
            )

    print(f"Task id: {task.id}")
    print(f"Task output: \n{task_output}")

# Save to file
output_file = os.path.join(
    os.path.dirname(__file__),
    f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
)
with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

rprint(f"\n[green]Results saved to: {output_file}[/green]")
print(StructureVisualizer(workflow).to_url())

rprint("\n[green]Workflow completed successfully![/green]")
