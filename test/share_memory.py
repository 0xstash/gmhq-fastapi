from griptape.structures import Workflow, Agent
from griptape.tasks import PromptTask
from griptape.utils import Chat
from dotenv import load_dotenv

load_dotenv()

workflow = Workflow(tasks=[PromptTask("Generate a joke on Real Madrid")])

workflow.run()

agent = Agent(conversation_memory=workflow.conversation_memory)

Chat(structure=agent).start()
