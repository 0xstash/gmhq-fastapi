import os
import sys
import logging
import json
from questionary import text, select

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
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
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

# Prompt user to select a company
selected_company = select("Select a company to analyze:", choices=company_choices).ask()

# Get the selected company's information
selected_company_name = selected_company.split(" - ")[0]
user_information_selected = next(
    user for user in user_information if user["company"] == selected_company_name
)


# Defaults.drivers_config = OpenAiDriversConfig(
#     prompt_driver=OpenAiChatPromptDriver(model="gpt-4o", stream=True)
# )

Defaults.drivers_config = AnthropicDriversConfig(
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-sonnet-20241022", stream=True)
)

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())


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

Here are two examples of well-constructed search keywords with relevance explanations. Never mind the quotation marks.:

1. "late reported earnings release" "compliance issue finance" "SEC fines firm" "granted license" "hiring for compliance"
   Relevance: This query targets high-level decision-makers in finance who may be experiencing difficulties that the company's solution could address, while excluding job postings.

2. "raised funding" "supply chain" "inefficiencies" "logistics waste" "layoffs"
   Relevance: This query focuses on recently funded companies in the supply chain sector that might be looking to improve their operations, using a reputable tech news source.

3. "tender published swimming facilities" "tender offer social facility austria" "swimming pool tender in Germany" 
    Relevance: These keywords are meant to find and target companies who have submitted requests for proposals or tenders for a swimming pool construction in Germany. 

Remember, the goal is to create queries that will lead to meaningful signals of potential customer need, always keeping in mind the ideal customer profile and the company's solution.   
Also remember, noone really publishes their pain points or needs exactly as they are. We have to infer them by searching for things that could point to these. 
Value props of {{company_name}}: {{value_props}}
Ideal customer profile: {{ideal_customer_profile}}
    """,
    context={
        "company_name": user_information_selected["company"],
        "value_props": user_information_selected["value_props"],
        "ideal_customer_profile": user_information_selected["ideal_customer_profile"],
    },
    id="signal_search_task",
    prompt_driver=AnthropicPromptDriver(
        model="claude-3-5-sonnet-20241022", stream=True
    ),
)

search_task = PromptTask(
    """
You are an AI assistant tasked with analyzing web content to identify potential buying signals for a B2B company based on search queries. Your goal is to scour the web, scrape relevant websites, and extract information that indicates potential customers who may benefit from the company's solution.

First, carefully review the company's profile:
<company_profile>
Company name: {{company_name}}
Product description: {{product_description}}
Value props: {{value_props}}
Ideal customer profile: {{ideal_customer_profile}}
</company_profile>

Now, examine the keywords from the following search queries that have been generated based on the company's ideal customer profile and solution:

<search_queries>
{{parent_outputs['signal_search_task']}}
</search_queries>

Your task is to use these search queries and keywords to find and analyze relevant web content. Follow these steps:

1. For each search query, use web search to find the most relevant results.
    a. Also use news_web_search_tool to query for news
2. Scrape the content from each of these web pages, focusing on the main text, headlines, and any structured data that might be relevant.
3. Analyze the scraped content to identify potential buying signals, such as:
   a. Expressions of pain points or challenges related to the company's solution
   b. Indications of growth or change that might necessitate the company's solution
   c. Announcements of initiatives or projects that align with the company's offerings
   d. Evidence of industry trends that the company's solution addresses

4. For each potential buying signal you identify, provide the following information in your output:
   a. The search query that led to this result
   b. The URL of the source
   c. A brief summary of the relevant content (2-3 sentences)
   d. An explanation of why this constitutes a potential buying signal (1-2 sentences)
   e. A confidence score (1-10) indicating how strong you believe this buying signal is

Present your findings in the following format:

<buying_signal>
<url>[Insert the source URL]</url>
<summary>[Insert your brief summary]</summary>
<relevance>[Insert your explanation of relevance]</relevance>
<confidence>[Insert your confidence score]</confidence>
</buying_signal>

Here are two examples of well-formatted outputs:

<buying_signal>
<url>https://www.cfodive.com/news/cfo-automation-financial-reporting-challenges</url>
<summary>The article discusses how CFOs are increasingly turning to automation solutions to address financial reporting challenges. It mentions that 67% of CFOs surveyed reported difficulties in meeting compliance deadlines due to manual processes.</summary>
<relevance>This indicates a widespread pain point among CFOs that aligns directly with the company's financial automation solution, suggesting a potential market opportunity.</relevance>
<confidence>9</confidence>
</buying_signal>

<buying_signal>
<url>https://techcrunch.com/2023/04/15/logisticorp-raises-50m-series-b-to-tackle-supply-chain-bottlenecks</url>
<summary>LogistiCorp, a rapidly growing e-commerce fulfillment company, has just raised a $50M Series B round. The CEO states that they plan to use the funding to optimize their logistics operations and reduce inefficiencies in their supply chain.</summary>
<relevance>This funding announcement, coupled with the stated intention to improve supply chain efficiency, suggests that LogistiCorp could be a potential customer for the company's supply chain optimization solution.</relevance>
<confidence>8</confidence>
</buying_signal>

Remember to:
- Focus on finding genuine, rational connections between the web content and potential buying signals.
- Avoid forced logic or stretching relevance. The signals should be actionable upon by reaching out to the target lead based on the signal.
- Ensure that your confidence scores accurately reflect the strength of the buying signal.
- Provide a diverse range of buying signals from different sources and queries.
- Respect website terms of service and robots.txt files when scraping content.

Your goal is to provide actionable insights that the B2B company can use to identify and pursue potential customers. Good luck!
    """,
    tools=[
        WebSearchTool(
            web_search_driver=SerperWebSearchDriver(
                api_key=os.getenv("SERPER_API_KEY"), date_range="d"
            )
        ),
        news_web_search_tool,
        web_scraper_tool,
        PromptSummaryTool(),
    ],
    id="search_task",
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o", stream=True),
    context={
        "company_name": user_information_selected["company"],
        "value_props": user_information_selected["value_props"],
        "ideal_customer_profile": user_information_selected["ideal_customer_profile"],
        "product_description": user_information_selected["product_description"],
    },
)


tasks = []
tasks.append(signal_search_task)
tasks.append(search_task)

signal_search_task.add_child(search_task)

workflow = Workflow(tasks=[*tasks])

print(StructureVisualizer(workflow).to_url())

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
