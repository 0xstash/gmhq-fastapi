from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

messages = [
    {
        "role": "system",
        "content": (
            "You are an artificial intelligence assistant and you need to "
            "engage in a helpful, detailed, polite conversation with a user."
        ),
    },
    {
        "role": "user",
        "content": ("How many stars are in the universe?"),
    },
]

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai"
)

# chat completion without streaming
response = client.chat.completions.create(
    model="sonar-pro",
    messages=messages,
)
print(response)

# chat completion with streaming
response_stream = client.chat.completions.create(
    model="sonar-pro",
    messages=messages,
    stream=True,
)
for response in response_stream:
    print(response)
