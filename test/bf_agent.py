import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.structures import Agent
from griptape.tools import FileManagerTool, PromptImageGenerationTool
from extension.drivers.black_forest_image_generation_driver.black_forest_image_generation_driver import (
    BlackForestImageGenerationDriver,
)

from dotenv import load_dotenv

load_dotenv()
agent = Agent(
    tools=[
        PromptImageGenerationTool(
            image_generation_driver=BlackForestImageGenerationDriver(
                model="flux-pro-1.1", api_key=os.getenv("BFL_API_KEY")
            ),
            off_prompt=True,
        ),
        FileManagerTool(),
    ]
)

agent.run(
    "Save a cinematic, realistic picture of a dog riding a skateboard to the assets directory as dog_skateboard_cinematic.jpeg"
)
