from dotenv import load_dotenv
import os
import logging
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.system_prompts import CHAT_PROMPT, ARTIFACT_PROMPT
from griptape.utils import Chat
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import DateTimeTool
from griptape.rules import Rule, Ruleset
from griptape.tasks import PromptTask, ToolkitTask
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
)


load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

ruleset = Ruleset(
    name="Pirate ruleset",
    rules=[
        Rule(f"{ARTIFACT_PROMPT}"),
        Rule(
            """You have to always respond in pirate. 
            Also always start with a joke. Lastly, first word should always be "cherry" """
        ),
    ],
)

rule_agent = Agent(rulesets=[ruleset])

overriddgen_agent = Agent()

overriddgen_agent.add_task(
    PromptTask(
        generate_system_template=lambda task: f"{ARTIFACT_PROMPT}"
        + """You have to always respond in pirate. 
            Also always start with a joke. Lastly, first word should always be 'cherry' """
    )
)


rule_output = rule_agent.run("who are you")
overriddgen_output = overriddgen_agent.run("who are you")

print("Rule agent output:" + rule_output.output_task.output.value)
print("Overriddgen agent output:" + overriddgen_output.output_task.output.value)
