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


def load_person_timeline():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define file path relative to the script location
    person_timeline_file = os.path.join(script_dir, "person_timeline.json")

    # Check if file exists
    if not os.path.exists(person_timeline_file):
        print(f"Error: File not found: {person_timeline_file}")
        return {
            "timestamp": datetime.now().isoformat(),
            "total_people": 0,
            "people": [],
        }

    with open(person_timeline_file, "r") as f:
        return json.load(f)


people = load_person_timeline()
print_json(data=people["people"][0])

# Define the number of people to process
NUM_PEOPLE_TO_PROCESS = questionary.text(
    "How many people would you like to process?",
    validate=lambda text: text.isdigit()
    and int(text) > 0
    and int(text) <= len(people["people"]),
    instruction="Enter a number between 1 and " + str(len(people["people"])),
).ask()

NUM_PEOPLE_TO_PROCESS = int(NUM_PEOPLE_TO_PROCESS)
rprint(f"[yellow]Will process {NUM_PEOPLE_TO_PROCESS} people.[/yellow]")

# Load user information using path relative to script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(
    os.path.dirname(script_dir)
)  # Go up two levels to project root
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


Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
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

            Always be factual and accurate about these details in your generation. 

            """
        ),
    ],
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

# Now proceed with processing using the confirmed number
tasks = []
for index, person in enumerate(people["people"][:NUM_PEOPLE_TO_PROCESS]):
    rprint(
        f"[blue]Processing:[/blue] [yellow]{person['name']}[/yellow] with email [green]{person['email']}[/green]"
    )

    followup_analysis_task = PromptTask(
        input="""
            
You are an AI assistant tasked with analyzing customer interactions for a sales team. Your goal is to determine whether a follow-up or check-in is warranted based on the recent email exchanges and meetings with a prospect or customer.
Your identity is as follows:
- Your first name: {{user_first_name}}
- Your last name: {{user_last_name}}
- Your email: {{user_email}}
- Your company: {{user_company}}

First, review the following interactions:

<interactions>
{{person}}
</interactions>

The current date is:
<current_date>{{today_date}}</current_date>

Analyze the interactions carefully, paying attention to the following aspects:
1. The recency of the last interaction
2. The nature and tone of the conversations
3. Any open questions or unresolved issues
4. Promises or commitments made by either party
5. The overall engagement level of the prospect/customer
6. Mind that we will exclusively look to follow on emails that are sales and customer conversations for the sale of {{user_company}}. If it is about something else, mark it as no follow-up needed.
7. Some interactions are initiated and run by a colleague of yours. Best way to check this is the domain name of the sender of the email and {{user_company}} If that is the case, mark it as no follow-up needed.
8. If the last interaction was a meeting conducted, a follow up is needed to either summarise or follow up with next steps regarding the meeting.

Consider that a follow-up may be necessary if:
- The last interaction was more than 7 days ago
- There are unanswered questions or unaddressed concerns
- The salesperson promised to provide additional information or take action
- The prospect/customer showed interest but didn't commit to a next step
- The conversation ended abruptly or without a clear conclusion

However, a follow-up might not be needed if:
- The last interaction was very recent (within the last 2-3 days)
- The prospect/customer explicitly stated they need time before the next interaction
- All questions were answered and next steps were clearly defined
- The prospect/customer indicated they are not interested or it's not the right time

Based on your analysis, provide a recommendation on whether a follow-up is needed. Include a brief explanation of your reasoning.

Present your results in the following terms: 
- follow_up_needed: [Yes/No]
- explanation: [Provide a short andconcise (max 2 sentences) explanation of your analysis and the key factors that influenced your decision] 
- thread_id_to_follow_up: [The thread ID (thread_id) of the interaction that the follow up should be sent to]
            """,
        output_schema=schema.Schema(
            {
                "follow_up_analysis": {
                    "follow_up_needed": bool,
                    "explanation": str,
                    "thread_id_to_follow_up": str,
                }
            }
        ),
        id=f"followup_analysis_{index}",
        rulesets=[identity_ruleset],
        context={
            "person": person,
            "today_date": datetime.now().strftime("%Y-%m-%d"),
            "user_first_name": user_information_selected["first_name"]
            + " "
            + user_information_selected["last_name"],
            "user_email": user_information_selected["email"],
            "user_company": user_information_selected["company"],
        },
    )

    tasks.append(followup_analysis_task)

# Initialize output data structure before running the workflow
output_data = {
    "analysis_timestamp": datetime.now().isoformat(),
    "total_people_analyzed": len(people["people"][:NUM_PEOPLE_TO_PROCESS]),
    "user_company": user_information_selected["company"],
    "follow_up_results": [],
}

workflow = Workflow(tasks=[*tasks])
print(StructureVisualizer(workflow).to_url())

workflow.run()

# Process all task results and collect them in the output data structure
for task in workflow.tasks:
    task_output = task.output.value if task.output else None

    # Extract the person index from the task ID
    task_id_parts = task.id.split("_")
    if len(task_id_parts) > 1:
        person_index = int(task_id_parts[-1])
        person_data = people["people"][person_index]

        # Process the nested follow_up_analysis structure
        if task_output and "follow_up_analysis" in task_output:
            analysis = task_output["follow_up_analysis"]

            # Create a more accessible result structure
            result = {
                "task_id": task.id,
                "person_name": person_data.get("name", "Unknown"),
                "person_email": person_data.get("email", "Unknown"),
                "follow_up_needed": analysis.get("follow_up_needed", False),
                "explanation": analysis.get("explanation", ""),
                "thread_id_to_follow_up": analysis.get("thread_id_to_follow_up", ""),
            }

            # Add this person's analysis to the results collection
            output_data["follow_up_results"].append(result)
        else:
            # Handle case where output doesn't match expected structure
            output_data["follow_up_results"].append(
                {
                    "task_id": task.id,
                    "person_name": person_data.get("name", "Unknown"),
                    "person_email": person_data.get("email", "Unknown"),
                    "error": "Invalid output format",
                    "raw_output": task_output,
                }
            )

    # Print task results to console
    print(f"Task id: {task.id}")
    if task_output and "follow_up_analysis" in task_output:
        analysis = task_output["follow_up_analysis"]
        print(f"Follow-up needed: {analysis.get('follow_up_needed', False)}")
        print(f"Explanation: {analysis.get('explanation', '')}")
    else:
        print(f"Task output: \n{task_output}")
    print("-" * 80)

# After collecting all results, sort them so follow-ups needed appear first
output_data["follow_up_results"] = sorted(
    output_data["follow_up_results"],
    key=lambda x: (not x.get("follow_up_needed", False)),
)

# Save all results to a single file with timestamp
output_file = os.path.join(
    os.path.dirname(__file__),
    f"followup_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
)

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

# Count how many follow-ups are needed for the summary
follow_ups_count = sum(
    1
    for result in output_data["follow_up_results"]
    if result.get("follow_up_needed", False)
)

rprint(f"\n[green]Analysis results saved to: {output_file}[/green]")
rprint(
    f"[yellow]Found {follow_ups_count} out of {len(output_data['follow_up_results'])} contacts requiring follow-up[/yellow]"
)
