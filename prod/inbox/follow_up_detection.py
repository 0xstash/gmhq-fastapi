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

# for person in people["people"]:
#     rprint(f"[green]{person['email']}[/green]")

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
web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)


tasks = []
for index, person in enumerate(people["people"][:10]):
    rprint(
        f"[blue]Processing:[/blue] [yellow]{person['name']}[/yellow] with email [green]{person['email']}[/green]"
    )

    followup_analysis_task = PromptTask(
        input="""
You are a professional sales and customer success assistant. I'm providing you with communication data for a specific person from my network, including both email threads and calendar meetings. Your task is to determine if a business-critical follow-up is needed to advance a deal or support a customer.
Today's date is: {{today_date}}
ANALYSIS INSTRUCTIONS:

STEP 1: TIMELINE ASSESSMENT
Begin by analyzing the chronology of our interactions:
- When was our most recent interaction (email or meeting)?
- How much time has elapsed since that interaction?
- Was our last interaction a meeting? (Meetings almost always require follow-up)
- Has there been an unusually long gap in communication for this relationship?

Apply these timeline rules:
- If our last interaction was a meeting and there's been no follow-up email within 2 business days, a follow-up is needed
- If it's been more than 14 days since our last communication with an active prospect, consider a follow-up
- If it's been more than 30 days since our last communication with an existing customer, consider a check-in

STEP 2: BUSINESS RELEVANCE ASSESSMENT
Determine if this contact represents a potential or existing customer/prospect with business value:
- Is this a prospect in an active sales cycle?
- Is this an existing customer who might need support?
- Is this a strategic partnership opportunity?

If this is merely a marketing email, newsletter, cold outreach with no response, or non-business conversation, mark it as NO FOLLOW-UP NEEDED and stop analysis.

STEP 3: FOLLOW-UP NECESSITY ASSESSMENT
For business-relevant contacts only, determine whether a follow-up is needed by checking:
- Are there unanswered questions about our product/service/pricing?
- Is there an open sales opportunity that hasn't progressed recently?
- Were there commitments made that need confirmation or completion?
- Were there action items from meetings that haven't been addressed?
- Did we discuss next steps that haven't been scheduled or executed?
- Has a promising conversation gone cold without clear resolution?
- If the request or the question of the customer is answered, then no follow-up is needed except to check in. 

Provide a clear YES or NO assessment on whether follow-up is needed, with a brief explanation.

IF AND ONLY IF follow-up is necessary, continue with the detailed analysis below:

STEP 4: DETAILED ANALYSIS

1. DEAL/RELATIONSHIP STATUS
   - What stage is this deal or customer relationship in?
   - What is the potential business value of this relationship?
   - What are the current blockers or open questions in this deal/relationship?

2. CONVERSATION STATUS
   - What specific questions or requests remain unanswered?
   - What commitments did we make that need follow-up?
   - What information did they request that we haven't provided?
   - What was the last action taken and by whom?

3. FOLLOW-UP STRATEGY
   - What specific information or proposal should we provide next?
   - What objections or concerns should we address?
   - What is the appropriate tone and urgency for this follow-up?
   - What specific call-to-action should we include?

Please format your response in the following sections:

1. Follow-Up Necessity: [YES/NO with brief explanation]

If YES, continue with:

1. Timeline Context (last interaction date, elapsed time, meeting follow-up status)
2. Business Context (deal stage, relationship value, current blockers)
3. Recommended Action (specific next steps with rationale)
4. Suggested Message Points (key elements to include in follow-up)

Your analysis should be strictly focused on business-critical communications that can advance deals or support customers. Ignore marketing emails, newsletters, or conversations without clear business potential.

Data to analyse below: 
- Data on our interactions: {{person}}
            """,
        output_schema=schema.Schema(
            {
                "follow_up_analysis": {
                    "follow_up_needed": bool,
                    "explanation": str,
                    "timeline_context": str,
                    "business_context": str,
                    "recommended_action": str,
                    "suggested_message_points": str,
                }
            }
        ),
        id=f"followup_analysis_{index}",
        rulesets=[identity_ruleset],
        context={"person": person, "today_date": datetime.now().strftime("%Y-%m-%d")},
    )

    tasks.append(followup_analysis_task)

# Initialize output data structure before running the workflow
output_data = {
    "analysis_timestamp": datetime.now().isoformat(),
    "total_people_analyzed": len(people["people"][:10]),
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
                "timeline_context": analysis.get("timeline_context", ""),
                "business_context": analysis.get("business_context", ""),
                "follow_up_priority": analysis.get("follow_up_priority", "N/A"),
                "recommended_action": analysis.get("recommended_action", ""),
                "suggested_message_points": analysis.get(
                    "suggested_message_points", ""
                ),
                "optimal_timing": analysis.get("optimal_timing", ""),
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
        if analysis.get("follow_up_needed", False):
            print(f"Priority: {analysis.get('follow_up_priority', 'N/A')}")
            print(f"Recommended action: {analysis.get('recommended_action', '')}")
    else:
        print(f"Task output: \n{task_output}")
    print("-" * 80)

# Save all results to a single file with timestamp
output_file = os.path.join(
    os.path.dirname(__file__),
    f"followup_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
)

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

# Also create a filtered version with only follow-ups needed
follow_ups_needed = {
    "analysis_timestamp": output_data["analysis_timestamp"],
    "user_company": output_data["user_company"],
    "follow_up_results": [
        result
        for result in output_data["follow_up_results"]
        if result.get("follow_up_needed", False)
    ],
}

if follow_ups_needed["follow_up_results"]:
    follow_ups_file = os.path.join(
        os.path.dirname(__file__),
        f"followup_needed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(follow_ups_file, "w") as f:
        json.dump(follow_ups_needed, f, indent=2)

    rprint(f"\n[green]All analysis results saved to: {output_file}[/green]")
    rprint(f"[green]Follow-ups needed saved to: {follow_ups_file}[/green]")
    rprint(
        f"[yellow]Found {len(follow_ups_needed['follow_up_results'])} contacts requiring follow-up[/yellow]"
    )
else:
    rprint(f"\n[green]All analysis results saved to: {output_file}[/green]")
    rprint("[blue]No follow-ups needed at this time[/blue]")
