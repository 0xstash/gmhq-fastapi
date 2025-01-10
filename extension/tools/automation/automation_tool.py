import os
import sys
import json
import schema
from schema import Literal, Schema, Or
import logging
import datetime

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


def create_workflow() -> Workflow:
    analyse_inputs = PromptTask(
        """
        Break down the automation request into discrete steps.
        Come up with the inputs required for the automation request. Think of it as if these inputs will be displayed in a form.
        Follow these guidelines:
        - Only come up with minimally required inputs. Example: If the request is an invoice extraction app, only the invoice file is required as an input.
        - If a file input is required, we can handle reading files without OCR. Such a step is not necessary.
        - Never come up with inputs that require integrations to other tools.
        - Only output required inputs.

        Output the results in YAML format.


        For each required input, provide:
        - A clear variable
        - A UI friendly input variable name to be shown to user (display_name)
        - A description of the input
        - The data type of the input (can be only one of the following: string, number, boolean, file)
        - Whether it's required or optional

        Format the response in YAML that matches this structure:
        required inputs:
        - variable_name: string
          display_name: string
          description: string
          type: string
          required: boolean (yes or no)
The automation request:
{{args[0]}}
        """,
        id="analyse_inputs",
    )

    step_analysis = PromptTask(
        """
Based on the automation request and the inputs, break down the automation request into discrete steps.
Your task is to break down a user's high-level request into actionable workflow steps. Each step should include:

1. A **specific AI prompt** for the step.
2. List of input names required for the step.
3. Name to reference this step's output in subsequent steps
4. List of step numbers whose outputs are used as inputs
5. List of tools necessary for the step

Follow these guidelines:
- Workflows start with the actions directly. There is no need for a step that asks for the user's input. Assume that you have all the inputs available.
- Analyze the user's request to identify the key tasks required.
- Think of each step as a distinct action or process within the workflow.
- Generate clear and detailed prompts for each step that an AI can use to complete it.
- Ensure the steps are logically sequenced and relevant to the user's goal.
- Never come up with steps that require integrations to other platforms. Example: You can extract an invoice but you cannot upload it to Xero. Another exampe: You can create a Linkedin post content but you cannot post it to Linkedin.
- Only come up with steps to execute the request. No validations or further feedback steps necessary.
- There should never be a preprocessing step or a postprocessing step or a summary step or a validation step or a step where you output a file. No step should also include "extract all information" or "analyze the data" or variations of these generic steps.
- The output of the workflow should always end with the final expected result.
- Always use one tool per step. NEVER use more than one tool per step. Only exception is using web search and web scraper in the same tool

List of the tools available:
- Websearch
- Webscraper
- Leadsearch
- Financial
- Filetool
- Gmailtool
- Imagegenerationtool

The automation request: {{args[0]}}
The inputs: {{parents_output_text}}
""",
        id="step_analysis",
    )

    yaml_output = PromptTask(
        """
Based on the provided inputs and workflow steps, structure the information into a precise format.

Inputs analysis: {{parent_outputs['analyse_inputs']}}
Steps analysis: {{parent_outputs['step_analysis']}}

Your task is to structure this information into the following format:

required_inputs:
- Each input should have:
  - name: the identifier for the input
  - description: clear explanation of what this input is for
  - type: must be one of: string, number, boolean, file
  - required: true/false indicating if this is mandatory

workflow_steps:
- Each step should have:
  - step_number: sequential number starting from 1
  - instruction: the specific prompt/instruction for the AI model (IMPORTANT: mention input variables directly without using curly braces)
  - required_inputs: list of input names needed for this step
  - uses_output_from_step: list of step numbers whose outputs are used (or null if none)
  - output_variable_name: unique name to reference this step's output

Example instruction format:
✓ "Extract invoice_number and recipient_name from the invoice"
✗ "Extract {invoice_number} and {recipient_name} from the invoice"

IMPORTANT:
- Never output a final_output section
- Never use curly braces {} around variables in instructions
Structure the above information precisely, ensuring all fields are properly filled and the format matches exactly.
""",
        id="yaml_output",
    )

    tasks = []
    tasks.append(analyse_inputs)
    tasks.append(step_analysis)
    tasks.append(yaml_output)
    analyse_inputs.add_child(step_analysis)
    step_analysis.add_child(yaml_output)
    return Workflow(tasks=[*tasks])
