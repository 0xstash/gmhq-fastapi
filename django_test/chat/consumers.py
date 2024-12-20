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
        from griptape.tools import DateTimeTool
        from griptape.events import (
            BaseEvent,
            EventListener,
            EventBus,
            StartActionsSubtaskEvent,
        )

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
        agent.add_task(
            ToolkitTask(
                query,
                prompt_driver=prompt_driver,
                tools=[
                    DateTimeTool(),
                ],
            )
        )

        def handler(event: BaseEvent):
            print("Task started!")
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
                    # Send the tool data
                    asyncio.create_task(self.send(text_data=tool_data))

        EventBus.add_event_listeners(
            [
                EventListener(
                    handler,
                    event_types=[
                        StartActionsSubtaskEvent,
                    ],
                )
            ]
        )
        agent.run()
