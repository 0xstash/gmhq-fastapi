import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.tasks import ToolkitTask
from griptape.structures import Agent
from griptape.artifacts import BaseArtifact, ErrorArtifact
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.tools import DateTimeTool
from tools.tool import ArtifactGenerationTool

from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)


class ToolsTask(ToolkitTask):
    def try_run(self) -> BaseArtifact:
        from griptape.tasks import ActionsSubtask

        self.subtasks.clear()

        result = self.prompt_driver.run(self.prompt_stack)
        subtask = self.add_subtask(ActionsSubtask(result.to_artifact()))
        last_tool_output = None

        while True:
            if subtask.output is None:
                if len(self.subtasks) >= self.max_subtasks:
                    subtask.output = ErrorArtifact(
                        f"Exceeded tool limit of {self.max_subtasks} subtasks per task"
                    )
                else:
                    last_tool_output = subtask.run()

                    result = self.prompt_driver.run(self.prompt_stack)
                    subtask = self.add_subtask(ActionsSubtask(result.to_artifact()))
            else:
                break

        return last_tool_output or subtask.output


agent = Agent()

agent.add_task(
    ToolsTask(
        "Create a short story on today's date",
        tools=[DateTimeTool(), ArtifactGenerationTool()],
    )
)

agent.run()
