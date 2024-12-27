import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.structures import Agent
from griptape.tools import PromptSummaryTool
from griptape.drivers import OpenAiChatPromptDriver
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from extension.tools.apollo.apollo_tool import ApolloClient
from dotenv import load_dotenv


load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

apollo_tool = ApolloClient(api_key=os.getenv("APOLLO_API_KEY"))

agent = Agent(tools=[apollo_tool, PromptSummaryTool()])
agent.run(
    """
please find me founders and cofounders of software startups in new york and amsterdam. The size can be between 50 to 150 people. 
    """
)
