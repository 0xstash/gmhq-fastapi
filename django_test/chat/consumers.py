from channels.generic.websocket import AsyncWebsocketConsumer
import os
from dotenv import load_dotenv
import json
import asyncio

load_dotenv()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        from griptape.drivers import OpenAiChatPromptDriver
        from griptape.structures import Agent
        from griptape.tasks import ToolkitTask
        from griptape.tools import DateTimeTool, WebSearchTool
        from griptape.drivers import GoogleWebSearchDriver
        from griptape.utils import Events
        from griptape.events import StartActionsSubtaskEvent

        try:
            data = json.loads(text_data)
            print(f"Parsed data: {data}")
        except Exception as e:
            print("Data parsing failed: " + str(e))
            data = {}

        query = data.get("message")
        print(f"Query: {query}")

        prompt_driver = OpenAiChatPromptDriver(
            model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"), stream=True
        )
        agent = Agent(stream=True)
        web_search_tool = WebSearchTool(
            web_search_driver=GoogleWebSearchDriver(
                api_key=os.environ["GOOGLE_API_KEY"],
                search_id=os.environ["GOOGLE_API_SEARCH_ID"],
                results_count=5,
                language="en",
                country="us",
            )
        )
        agent.add_task(
            ToolkitTask(
                query,
                prompt_driver=prompt_driver,
                tools=[DateTimeTool(), web_search_tool],
            )
        )

        async def send_event(event):
            if isinstance(event, StartActionsSubtaskEvent):
                if event.subtask_actions:
                    tool_name = None
                    for action in event.subtask_actions:
                        tool_name = action.get("name")
                        if tool_name:
                            break

                    if tool_name:
                        tool_data = (
                            "[TOOL_START] "
                            + tool_name
                            + "|"
                            + str(event.task_id)
                            + "|"
                            + str(int(event.timestamp))
                            + " [TOOL_END]"
                        )
                        await self.send(text_data=tool_data)

        # Use the new Events utility
        for event in Events(agent).run():
            await send_event(event)
