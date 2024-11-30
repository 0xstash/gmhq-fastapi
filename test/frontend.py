from fasthtml.common import *
import httpx
import asyncio

app, rt = fast_app(
    hdrs=(
        Style(
            """
            .main-grid {
                display: grid;
                grid-template-columns: 2fr 1fr; /* Adjust the ratio as needed */
                gap: 20px;
            }
            .chat-display {
                border: 1px solid #ccc;
                padding: 10px;
                margin-top: 10px;
                height: 300px;
                overflow-y: scroll;
            }
            form {
                margin-bottom: 10px;
            }
            .left-section {
                /* Additional styles for the left section if needed */
            }
            .right-section {
                /* Styles for the right section */
                border: 1px solid #ccc;
                padding: 10px;
                height: 300px;
            }
            """
        ),
    )
)

# A simple in-memory store for messages
messages = []

# Initialize a separate in-memory store for action messages
action_messages = []


@rt("/frontend")
def get():
    return Titled(
        "Chat Application",
        Grid(
            Div(
                Form(
                    Input(
                        id="message",
                        name="message",
                        placeholder="Type your message here...",
                    ),
                    Button("Send", type="submit"),
                    hx_post="/frontend/send",
                    hx_target="#chat-display",
                    hx_swap="beforeend",
                ),
                Div(
                    id="chat-display",
                    cls="chat-display",
                    hx_ext="sse",
                    sse_connect="/frontend/stream",
                    hx_swap="beforeend",
                ),
                cls="left-section",
            ),
            Div(
                P("This is the right-hand section."),
                Div(
                    id="action-display",
                    cls="chat-display",
                    hx_ext="sse",
                    sse_connect="/frontend/action-stream",
                    hx_swap="beforeend",
                ),
                cls="right-section",
            ),
            cls="main-grid",
        ),
    )


@rt("/frontend/send")
def post(message: str):
    try:
        # Send the message to the FastAPI backend
        response = httpx.post(
            "http://localhost:8000/api/chat", json={"message": message}
        )
        response.raise_for_status()  # Raise an error for bad responses
        chat_response = response.json().get("response", "No response")

        # Simulate action event handling
        action_event = "Simulated Action Event"  # Replace with actual action event data
        action_messages.append(action_event)

    except httpx.HTTPStatusError as e:
        chat_response = f"Error: {e.response.status_code}"
    except Exception as e:
        chat_response = f"Error: {str(e)}"

    # Store the message and response with line breaks
    messages.append(f">> {message}\n-- {chat_response}")

    # Return with line breaks
    return Div(f">> {message}\n-- {chat_response}")


@rt("/frontend/stream")
async def get():
    async def message_stream():
        last_index = 0
        while True:
            if last_index < len(messages):
                yield sse_message(Div(messages[last_index]))
                last_index += 1
            await asyncio.sleep(1)

    return EventStream(message_stream())


@rt("/frontend/action-stream")
async def get():
    async def action_stream():
        last_index = 0
        while True:
            if last_index < len(action_messages):
                yield sse_message(Div(action_messages[last_index]))
                last_index += 1
            await asyncio.sleep(1)

    return EventStream(action_stream())


serve()
