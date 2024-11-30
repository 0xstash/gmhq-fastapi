import logging

from griptape.configs import Defaults
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.structures import Agent
from griptape.tools import PromptSummaryTool, WebScraperTool, DateTimeTool
from griptape.utils import Stream, Chat


from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-40-mini")
)

# Hide Griptape's usual output
logging.getLogger(Defaults.logging_config.logger_name).setLevel(logging.ERROR)

agent = Agent(
    input="What is tomorrow's date from a year ago?",
    tools=[DateTimeTool()],
    stream=True,
)


for artifact in Chat(Stream(agent)).run():
    print(artifact.value, end="", flush=True)
