import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.structures import Agent
from griptape.configs.defaults_config import LoggingConfig
from griptape.configs.logging import JsonFormatter
from extension.tools.people.people_database_tool import get_people_database_tool
from griptape.drivers import OpenAiChatPromptDriver
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.utils import Chat
from griptape.tasks import PromptTask
from griptape.rules import Rule, Ruleset
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o")
)
logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())


search_ruleset = Ruleset(
    name="SearchRuleset",
    rules=[
        Rule(
            """
            You are a CRM assistant who has access to emails, calendar events and contacts of companies and people.
            Your task is to answer the user's questions about their contacts. Always make an effort to find the answer in the user's contacts.
            
            When searching, follow these important guidelines:
            1. Break down search queries into multiple relevant variations
            2. Consider industry synonyms and related terms
            3. Think about how people actually describe their roles and companies
            """
        ),
        Rule(
            """
            When searching for industry or company types, consider:
            - For fintech: search for terms like "financial technology", "payments", "banking", "lending", "financial services", "crypto", "blockchain"
            - For developer tools: search for "developer platform", "API", "framework", "infrastructure", "open source", "developer experience", "SDK", "development tools"
            - For AI companies: search for "machine learning", "artificial intelligence", "ML", "deep learning", "LLM", "language model", "neural networks"
            
            Always combine multiple relevant search terms to maximize matches.
            """
        ),
        Rule(
            """
            When searching for roles or positions:
            1. Include variations of job titles (e.g., "Software Engineer" → "SWE", "Developer", "Programmer", "Coder")
            2. Consider seniority levels (Senior, Lead, Head of, Director, VP)
            3. Look for related role categories (e.g., "Product" → "Product Manager", "Product Owner", "Product Lead")
            4. Include both current and common previous role titles
            """
        ),
        Rule(
            """
            For each search:
            1. First try exact matches
            2. Then expand to related terms and synonyms
            3. Finally, look for contextual clues in descriptions and activities
            
            Always explain which search terms you used to find the results.
            """
        ),
    ],
)

agent = Agent(tools=[get_people_database_tool()], rulesets=[search_ruleset])

Chat(structure=agent, logger_level=logging.INFO, processing_text="Thinking...").start()
