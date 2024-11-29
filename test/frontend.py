from fasthtml.common import *
import httpx
import asyncio

app, rt = fast_app(
    hdrs=(
        Style(
            """
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
        """
        ),
    )
)

# A simple in-memory store for messages
messages = []


@rt("/frontend")
def get():
    return Titled(
        "Chat Application",
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
    except httpx.HTTPStatusError as e:
        chat_response = f"Error: {e.response.status_code}"
    except Exception as e:
        chat_response = f"Error: {str(e)}"

    # Store the message and response
    messages.append(f">> {message}<br>-- {chat_response}")

    return Div(f">> {message}<br>-- {chat_response}")


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


serve()
