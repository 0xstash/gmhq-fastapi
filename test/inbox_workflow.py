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


logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)

signal_generation_task = PromptTask(
    """
Given:
[COMPANY NAME]: {{company_name}}
[VALUE PROPOSITIONS]: {{value_props}}
[IDEAL CUSTOMER PROFILE]: {{ideal_customer_profile}}

Your task is to generate specific search strategies that identify real buying signals. Think like a sales detective - what digital breadcrumbs indicate a company might need our solution?

Generate search strategies for these signal types:

1. People Movements & Changes
- New hires in relevant roles
- Leadership changes
- Team expansions
- Departures from key roles
- Job postings indicating pain points
- LinkedIn profile updates showing role changes

2. Growth & Change Signals
- Office expansions
- New market entries
- Product launches
- Customer announcements
- Partnership announcements
- Technology stack changes
- Process changes
- Regulatory compliance updates

3. Problem Indicators
- Negative feedback about competitors
- Public discussions of challenges we solve
- Questions about solutions in our space
- Comments about inefficiencies
- Social posts about process struggles
- Conference presentations about related challenges

4. Investment & Financial Signals
- Funding rounds
- Budget approvals
- Fiscal year changes
- Earnings calls mentions (public companies)
- Cost-cutting initiatives
- Efficiency programs

5. Digital Footprints
- Event attendance
- Webinar participation
- Content engagement
- Tool usage mentions
- Social media discussions
- Forum questions
- Industry group participation

For each category, provide:
1. Specific search strings using Boolean operators
2. Social media hashtags to monitor
3. Key phrases that indicate buying intent
4. Platform-specific search approaches

Output Format:
=============
For each signal type, output in this structure:

SIGNAL CATEGORY: [Name]

SEARCH QUERIES:
- 🔥 [High intent query]
- 🟡 [Medium intent query]
- 🟢 [Basic intent query]

PLATFORMS TO MONITOR:
[Specific platforms]

Remember:
- Include regional variations of terms
- Consider industry-specific language
- Focus on actionable signals, not generic content
- Think about seasonal or timing-based triggers
- Include both company and individual-level signals

Think beyond obvious signals. Examples:
- Company posts about process automation = potential need for workflow tools
- Finance team growth = possible need for reporting solutions
- Customer support team expansion = potential need for service tools
- Developer advocacy roles = API integration opportunities
- Risk officer hiring = compliance solution needs
- International expansion = localization tool needs
- Acquisition announcement = integration tool needs
- Event sponsorship = budget availability signals
- Product launch = scalability needs
    """,
    prompt_driver=OpenAiChatPromptDriver(
        model="o3-mini", temperature=NOT_GIVEN, stream=True
    ),
    context={
        "company_name": user_information_selected["company"],
        "value_props": user_information_selected["value_props"],
        "ideal_customer_profile": user_information_selected["ideal_customer_profile"],
    },
    id="signal_generation_task",
    max_subtasks=10,
)


tasks = []
tasks.append(signal_generation_task)

workflow = Workflow(tasks=[*tasks])

workflow_url = StructureVisualizer(workflow).to_url()
print(workflow_url)

log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
log_entry += f"Workflow Structure URL: {workflow_url}\n"
log_file = "test/data/event_logs.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)
existing_content = ""
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        existing_content = f.read()

with open(log_file, "w") as f:
    f.write(log_entry + existing_content)


workflow.run()

for task in workflow.tasks:
    log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
    log_entry += f"Task: {task.id} \n Output: \n {task.output}\n"
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
