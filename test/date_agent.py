from dotenv import load_dotenv
import os
import logging
import uuid

from griptape.utils import Chat
from griptape.tasks import PromptTask, ToolkitTask
from griptape.artifacts import ErrorArtifact, BaseArtifact, ListArtifact, TextArtifact
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import DateTimeTool
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.drivers import GriptapeCloudConversationMemoryDriver
from griptape.structures.structure import ConversationMemory
from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    BaseActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
    BaseChunkEvent,
)

from rich import print as rprint, print_json

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(
        model="gpt-4o-mini", stream=True, api_key=os.getenv("OPENAI_API_KEY")
    )
)

# Initialize a list to accumulate event logs
event_logs = []


def on_event(event: BaseEvent) -> None:
    if isinstance(event, BaseActionsSubtaskEvent):
        rprint(f"BaseActionsSubtaskEvent: {event.__class__.__name__}")
        rprint(f"Actions logged: {event.subtask_actions}")
        rprint(f"Subtask thought: {event.subtask_thought}")
        rprint(f"Basetask output: {event.task_output}")
        # Accumulate the subtask actions in the event_logs list
        event_logs.append(
            {
                "subtask_actions": event.subtask_actions,
                "subtask_thought": event.subtask_thought,
                "task_output": event.task_output,
            }
        )


EventBus.add_event_listeners(
    [
        EventListener(on_event, event_types=[BaseActionsSubtaskEvent, BaseChunkEvent]),
        EventListener(
            lambda e: print(str(e), end="", flush=True),
            event_types=[BaseChunkEvent],
        ),
    ]
)


class ToolsTask(ToolkitTask):
    def try_run(self) -> BaseArtifact:
        from griptape.tasks import ActionsSubtask

        self.subtasks.clear()

        result = self.prompt_driver.run(self.prompt_stack)
        subtask = self.add_subtask(ActionsSubtask(result.to_artifact()))
        tool_outputs = []

        while True:
            if subtask.output is None:
                if len(self.subtasks) >= self.max_subtasks:
                    subtask.output = ErrorArtifact(
                        f"Exceeded tool limit of {self.max_subtasks} subtasks per task"
                    )
                else:
                    tool_result = subtask.run()
                    # Wrap each tool output separately
                    if tool_result is not None:
                        tool_outputs.append(
                            TextArtifact(
                                f"<artifact_output>{tool_result}</artifact_output>"
                            )
                        )

                    result = self.prompt_driver.run(self.prompt_stack)
                    subtask = self.add_subtask(ActionsSubtask(result.to_artifact()))
            else:
                break

        return ListArtifact([subtask.output, *tool_outputs])


agent = Agent()
agent.add_task(ToolsTask(tools=[DateTimeTool()]))
agent.run("what is yesterday's date")

# Print all accumulated event logs at the end
# rprint("Accumulated Event Logs:")
# for log in event_logs:
#     rprint(log)
