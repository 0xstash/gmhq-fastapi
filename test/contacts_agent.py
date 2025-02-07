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
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o")
)
logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

agent = Agent()

agent.add_task(
    PromptTask(
        """You are a CRM assistant who has access to emails, calendar events and contacts of companies and people
    Your task is to answer the user's questions about their contacts. Always make an effort to find the answer in the user's contacts.
    Here is his or her query: {{args[0]}}
    """,
        tools=[get_people_database_tool()],
    )
)

Chat(structure=agent, logger_level=logging.INFO, processing_text="Thinking...").start()
