from fasthtml.common import *
import asyncio
from dotenv import load_dotenv
from griptape.structures import Agent
from griptape.drivers import OpenAiChatPromptDriver
from griptape.utils import Chat

load_dotenv()

tlink = (Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"),)
dlink = Link(
    rel="stylesheet",
    href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css",
)
app = FastHTML(hdrs=(tlink, dlink, picolink), ws_hdr=True)

messages = []

# Initialize Griptape Agent with OpenAI Chat Prompt Driver
agent = Agent(
    prompt_driver=OpenAiChatPromptDriver(
        api_key=os.environ["OPENAI_API_KEY"], model="gpt-3.5-turbo", temperature=0.1
    )
)


def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    role = "user" if msg["role"] == "user" else "assistant"
    bubble_class = f"chat-bubble-{'primary' if role == 'user' else 'secondary'}"
    chat_class = f"chat-{'end' if role == 'user' else 'start'}"
    return Div(
        Div(role, cls="chat-header"),
        Div(
            msg["content"],
            id=f"chat-content-{msg_idx}",
            cls=f"chat-bubble {bubble_class}",
        ),
        id=f"chat-message-{msg_idx}",
        cls=f"chat {chat_class}",
        **kwargs,
    )


def ChatInput():
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Type a message",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )


@app.route("/")
def get():
    page = Body(
        H1("Chatbot Demo"),
        Div(
            *[ChatMessage(idx) for idx in range(len(messages))],
            id="chatlist",
            cls="chat-box overflow-y-auto",
        ),
        Form(
            Group(ChatInput(), Button("Send", cls="btn btn-primary")),
            ws_send="",
            hx_ext="ws",
            ws_connect="/wscon",
            cls="flex space-x-2 mt-2",
        ),
        cls="p-4 max-w-lg mx-auto",
    )
    return Title("Chatbot Demo"), page


@app.ws("/wscon")
async def ws(msg: str, send):
    messages.append({"role": "user", "content": msg})

    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist")
    )
    await send(ChatInput())

    # Use Griptape Agent to generate a response
    response = agent.run(msg)
    messages.append({"role": "assistant", "content": response})

    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist")
    )


serve()
