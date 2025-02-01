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
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o")
)
logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

agent = Agent(tools=[get_people_database_tool()])

Chat(structure=agent, logger_level=logging.INFO, processing_text="Thinking...").start()
