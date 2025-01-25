import os
import sys
from rich import print as rprint
from rich import print_json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.drivers import OpenAiImageGenerationDriver
from griptape.engines import PromptImageGenerationEngine
from griptape.structures import Agent
from griptape.tools import PromptImageGenerationTool

# from artifact.artifact_agent import ArtifactAgent
from dotenv import load_dotenv


load_dotenv()

driver = OpenAiImageGenerationDriver(
    model="dall-e-2",
)

engine = PromptImageGenerationEngine(image_generation_driver=driver)

agent = Agent(
    tools=[
        PromptImageGenerationTool(
            engine=engine,
            output_dir="images",
        ),
    ]
)

output = agent.run("Generate a watercolor painting of a dog riding a skateboard")
rprint(f"FOR MERT Output of the task FOR MERT: {output.output_task.output.to_text()}")
