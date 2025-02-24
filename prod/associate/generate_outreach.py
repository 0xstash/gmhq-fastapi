import os
import sys
import logging
import json
import questionary
import re

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
from griptape.utils import Chat, Stream
from griptape.tasks import PromptTask
from griptape.rules import Ruleset, Rule
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

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

output_ruleset = Ruleset(
    name="Output rules",
    rules=[
        Rule(
            "Your tone should be casual and human. Each point you make should be clear and specific regarding the solutions or problems you talk about. Your content should create relevancy between you, your solution and the customer. "
        ),
        Rule(
            "Your output should always be around 40 to 50 words maximum. Always seperate each sentence as a paragraph. End your output with a signoff "
        ),
        Rule(
            "Your output should only be the body of the message. Never output a subject line or explanation. "
        ),
    ],
)

user_instructions = input("Enter your instructions: ")


def substitute_placeholders(user_instructions, contact_info):
    pattern = r"@([A-Za-z0-9_-]+)"
    placeholders = re.findall(pattern, user_instructions)
    modified_request = user_instructions

    # Create a set to hold the unique placeholder-value pairs
    added_placeholders = set()

    for placeholder in placeholders:
        if placeholder.lower() not in added_placeholders:
            value = contact_info.get(
                placeholder.lower(), f"Empty value for {placeholder}"
            )
            modified_request += f"\n{placeholder}: {value}"
            added_placeholders.add(placeholder.lower())

    print("Modified request:", modified_request)
    return modified_request
