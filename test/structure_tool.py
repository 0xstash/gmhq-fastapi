import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.system_prompts import CHAT_PROMPT, ARTIFACT_PROMPT
from griptape.configs import Defaults
from griptape.artifacts import BaseArtifact, ErrorArtifact, ListArtifact
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
from griptape.structures import Agent, Pipeline, Workflow
from griptape.drivers import (
    LocalStructureRunDriver,
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    GooglePromptDriver,
)
from griptape.tasks import ToolkitTask, StructureRunTask, PromptTask
from griptape.tools import StructureRunTool, WebSearchTool, DateTimeTool
from griptape.loaders import WebLoader
from griptape.rules import Rule, Ruleset
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from dotenv import load_dotenv

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)
# Defaults.drivers_config = AnthropicDriversConfig(
#     prompt_driver=AnthropicPromptDriver(model="claude-3-haiku-20240307")
# )


def visualisation_tool() -> Agent:
    visualisation_agent = Agent()
    visualisation_agent.add_task(
        PromptTask(
            generate_system_template=lambda task: "You are a joker pirate that always responds in jokes"
        )
    )
    return visualisation_agent


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

        return ListArtifact(
            [
                subtask.output,
                *([last_tool_output] if last_tool_output is not None else []),
            ]
        )


web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
structure_run_tool = StructureRunTool(
    description="Visualisation tool - Structure to invoke when a visualisation is required or a visualisation is requested or a visualisation can serve better to make the point.",
    structure_run_driver=LocalStructureRunDriver(create_structure=visualisation_tool),
)

agent = Agent(tools=[structure_run_tool, web_search_tool, DateTimeTool()])

agent.add_task(
    ToolsTask(
        "what are the biggest 2 news from today",
        tools=[structure_run_tool, web_search_tool, DateTimeTool()],
    )
)
agent.run()

# agent.run(
#     "Please find a recent news on Salesforce and create a joke around it to be able to tweet"
# )
