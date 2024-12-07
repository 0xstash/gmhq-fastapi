import os
import sys
from rich import print as rprint
from rich import print_json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from dotenv import load_dotenv
from artifact.artifact_agent import ArtifactAgent

load_dotenv()

# Configure the OpenAI driver
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

agent = ArtifactAgent()

output = agent.run(
    " Write Python code with Nicegui that displays a simple fancy auth page"
)

rprint(f"FOR MERT Output of the task FOR MERT: {output.output_task.output.to_text()}")
