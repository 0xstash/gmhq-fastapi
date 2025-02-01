from griptape.structures import Workflow
from griptape.tasks import ToolkitTask, PromptTask
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from dotenv import load_dotenv

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="")
)

task_1 = PromptTask("Multiple the number here by 2: {{args[0]}}", id="task_1")
task_2 = PromptTask(
    "Multiply the number by 4: {{parent_outputs['task_1']}}", id="task_2"
)

tasks = []

task_1.add_child(task_2)
tasks.append(task_1)
tasks.append(task_2)

workflow = Workflow(tasks=[*tasks])

output = workflow.run("10")

for task in workflow.tasks:
    print(f"Task: {task.id} output: {task.output}")

print(f"First task: {workflow.tasks[0].output.value}")
print(f"Second task: {workflow.tasks[1].output.value}")

print(
    f"Task outputs: {workflow.task_outputs}"
)  # dictionary with all task outputs including the values and named tasked ID
print(
    f"Output variable: {workflow.output}"
)  # output of the workflow - can be equal to workflow.output_task
print(f"Output task: {workflow.output_task}")  # output of the last task available
