import os
import sys
import logging
import json
import questionary
from datetime import datetime
import re
from rich.pretty import pprint

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent, Pipeline, Workflow

from griptape.utils import StructureVisualizer
from griptape.configs import Defaults
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
import schema
from griptape.utils import Chat, Stream
from griptape.tasks import PromptTask
from griptape.rules import Ruleset, Rule
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

# Use a relative path from the script location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
user_info_path = os.path.join(project_root, "test", "data", "user_information.json")

# Load user information
with open(user_info_path, "r") as file:
    user_information = json.load(file)

# Load research results
research_results_path = os.path.join(
    os.path.dirname(user_info_path), "research_results_20250401_011710.json"
)
with open(research_results_path, "r") as file:
    research_results = json.load(file)

contact_list_path = os.path.join(os.path.dirname(user_info_path), "contact_list.json")
with open(contact_list_path, "r") as file:
    contact_list = json.load(file)

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

# Extract research task and summary information
research_data = research_results["research_task"]["value"]
summary_data = research_results["summary_task"]["value"]

account_research = research_data + summary_data

# ---- Drivers ----
# Defaults.drivers_config = OpenAiDriversConfig(
#     prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True)
# )

Defaults.drivers_config = AnthropicDriversConfig(
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-haiku-20241022")
)

pprint(user_information_selected)
additional_instructions = questionary.text("Additional instructions: ").ask()
outreach_task = PromptTask(
    #     """You are a sales professional crafting a personalized, human-like outreach email.
    # You have to adhere to the following requirements and instructions:
    # 1. Writing style and tone:
    #    - Use short and casual sentences
    #    - Keep the overall email concise (aim for 4-5 sentences)
    #    - Keep each sentence short and simple.
    #    - Be friendly but professional
    #    - Use 5th grade language and always the simplest word for each term
    #    - Include a line break after each sentence
    #    - Write in a conversational tone
    # 2. Structure the email as follows:
    #    a. Greeting
    #    b. Brief and creative introduction. Use the account research done here. Avoid repeating what the recipient already knows and does as a company.
    #    c. Value proposition and pain point addressing
    #    d. Call to action
    #    e. Closing
    # 3. Authentic Connection
    # - Demonstrate that you've done research on the recipient and their company
    # - Use a genuine, specific insight about the company that is relevant to the recipient and our value propositions
    # - Avoid generic or automated-sounding language
    # - Sound like a real person, not a sales robot
    # 4. Targeted Value Proposition
    # - Address a specific, tangible business challenge
    # - Explain your solution in simple, clear terms
    # - Focus on the recipient's immediate gains
    # - Use conversational, straightforward language
    # 5. Natural Call to Action
    # - Make responding feel easy and low-pressure
    # - Be crystal clear about what you're asking
    # - Sound like you're talking to a colleague
    # Strict No-Go Zone:
    # - No corporate buzzwords
    # - No fabricated stories
    # - No overused sales phrases
    # - Zero automated-sounding text
    # Personalization Mandate:
    # - Reference verifiable company information
    # - Demonstrate real understanding of their context
    # - Create a human-to-human connection
    # Output Format (MANDATORY):
    # {
    #     "subject": "Concise, specific subject (5 words max)",
    #     "body": "Your conversational email text"
    # }
    # Formatting Rules:
    # - Subject: Short, specific
    # - Body: 4-5 sentences max
    # - Tone: Friendly, professional
    # - Language: Simple, clear
    # Priority Override:
    # If additional instructions are provided, they supersede previous guidelines.
    # 4. Additional instructions. If there are additional instructions provided, they are prioritised over the previous instructions:
    #     {{additional_instructions}}
    # Input variables to personalise the content:
    # Recipient full name: {{name}}
    # Recipient company: {{company}}
    # Recipient position: {{position}}
    # Account research done on recipient: {{account_research}}""",
    """
    You are an expert sales professional crafting a genuine, conversational outreach email.

Core Principles:
1. Sound like a real person
2. Be brutally simple
3. Focus on ONE clear value
4. Use zero sales fluff
5. Always end the email with my signature

Email Crafting Guidelines:
- Maximum 4-5 sentences
- Language a 5th grader understands
- No corporate jargon
- Personal, direct tone
- Show you've done real research

Research Approach:
1. Find ONE specific, recent company development
2. Connect that development to a SINGLE, clear solution. It HAS to be a clear, logical connection to our offer.
3. Make the value proposition crystal clear
4. Offer an easy, no-pressure next step

Strict Prohibitions:
- No marketing speak
- No made-up stories
- No generic phrases
- No over-promising
- No complex explanations
- No corporate jargon

Output Requirements:
{
    "subject": "Short, specific subject (max 5 words)",
    "body": "Conversational email text"
}

Personalization Elements:
- Recipient Name: {{name}}
- Company: {{company}}
- Position: {{position}}
- Specific Research: {{account_research}}

Golden Rule: Write like you're texting a work friend about a potential opportunity.
   """,
    id="outreach_task",
    rulesets=[identity_ruleset],
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-haiku-20241022"),
    context={
        "account_research": account_research,
        "additional_instructions": additional_instructions,
        "name": contact_list[2]["name"],
        "company": contact_list[2]["company"],
        "position": contact_list[2]["position"],
    },
    output_schema=schema.Schema({"subject": str, "body": str}),
)


pprint(contact_list[0]["name"])

tasks = []
tasks.append(outreach_task)

workflow = Workflow(tasks=[*tasks])

result = workflow.run()

try:
    output_dict = result.output.value
    if isinstance(output_dict, str):
        # If we got a string, try to parse it as JSON
        import json

        output_dict = json.loads(output_dict)

    # Format the complete email with subject and body
    formatted_output = f"Subject: {output_dict['subject']}\n\n{output_dict['body']}"
except (KeyError, json.JSONDecodeError, TypeError) as e:
    print(f"Error processing output: {e}")
    print("Raw output:", result.output.value)
    raise

# Save the output to a text file
output_file_path = os.path.join(
    os.path.dirname(user_info_path),
    f"outreach_email_{contact_list[0]['name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
)
with open(output_file_path, "w") as f:
    f.write(formatted_output)

print(f"\nEmail content has been saved to: {output_file_path}")
