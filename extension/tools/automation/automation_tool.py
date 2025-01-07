import os
import sys
import json
import schema
from schema import Literal, Schema, Or
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
from griptape.artifacts import BaseArtifact, ErrorArtifact, ListArtifact
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.structures import Agent, Pipeline, Workflow
from griptape.tools import WebScraperTool, WebSearchTool, PromptSummaryTool
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.rules import Rule, Ruleset
from griptape.tasks import PromptTask, ToolkitTask, ExtractionTask
from griptape.engines import JsonExtractionEngine
from griptape.utils import Chat
from dotenv import load_dotenv

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True)
)

json_extraction_engine = JsonExtractionEngine(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini"),
    template_schema=Schema(
        {
            Literal(
                "required_inputs", description="List of inputs required from the user"
            ): Schema(
                [
                    {
                        Literal("name", description="Name of the input field"): str,
                        Literal(
                            "description",
                            description="Description of what this input is for",
                        ): str,
                        Literal("type", description="Data type of the input"): str,
                        Literal(
                            "required", description="Whether this input is mandatory"
                        ): bool,
                    }
                ]
            ),
            Literal(
                "workflow_steps", description="Sequential steps to process the request"
            ): Schema(
                [
                    {
                        Literal("step_number", description="Order of execution"): int,
                        Literal(
                            "instruction",
                            description="Clear instruction/prompt to be sent to AI model",
                        ): str,
                        Literal(
                            "required_inputs",
                            description="List of input names needed for this step",
                        ): [str],
                        Literal(
                            "uses_output_from_step",
                            description="List of step numbers whose outputs are used as inputs",
                        ): Schema(Or([int], None)),
                        Literal(
                            "expected_output",
                            description="Description of the expected output from this step",
                        ): str,
                        Literal(
                            "output_variable_name",
                            description="Name to reference this step's output in subsequent steps",
                        ): str,
                    }
                ]
            ),
        }
    ).json_schema("AutomationSchema"),
)


def create_workflow() -> Workflow:
    task_1 = PromptTask(
        """You are an expert system designer tasked with breaking down user requests into structured workflows.
        Analyze the following query and create a detailed step-by-step workflow that an AI model can execute.

        Guidelines for workflow creation:
        1. First, identify all required inputs from the user that will be needed throughout the process
        2. Break down complex tasks into smaller, manageable steps
        3. Each step must have:
           - A clear, specific instruction for the AI
           - List of required inputs (both user inputs and outputs from previous steps)
           - Well-defined expected output that can be used by subsequent steps
        4. Ensure steps are ordered logically with clear data dependencies
        5. Use specific, actionable language in instructions
        6. Consider validation and error checking where appropriate

        Original Query: {{args[0]}}

        Create a workflow that will accomplish this request, making sure each step produces 
        concrete outputs that can be referenced by later steps if needed.""",
        id="task_1",
        prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
    )

    task_2 = ExtractionTask(
        """Based on the workflow description provided, extract and structure the information 
            into a formal specification following the schema requirements.

            Input Description: {{parent_output}}

            Convert the above workflow description into a structured format that includes:
            1. All required user inputs with their details
            2. Sequential workflow steps with their dependencies
            3. Clear input/output relationships between steps

            Ensure each step's instruction is specific and actionable, and all dependencies 
            are properly referenced using output_variable_names.""",
        id="task_2",
        extraction_engine=json_extraction_engine,
    )
    tasks = []
    tasks.append(task_1)
    tasks.append(task_2)
    task_1.add_child(task_2)
    return Workflow(tasks=[*tasks])
