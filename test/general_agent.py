import os
import sys
from rich import print as rprint
from rich import print_json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.tools import DateTimeTool, WebSearchTool
from dotenv import load_dotenv
from artifact.artifact_agent import ArtifactAgent
from drivers.serper_web_search_driver import SerperWebSearchDriver
from griptape.utils import Chat


load_dotenv()

# Configure the OpenAI driver
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)
web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
agent = ArtifactAgent(tools=[DateTimeTool()])

output = agent.run("create a calendar event app in shadcn style UI please")
rprint(f"FOR MERT Output of the task FOR MERT: {output.output_task.output.to_text()}")
