import asyncio
import websockets
import json


async def test_websocket():
    # Try different URL formats
    urls = [
        "ws://127.0.0.1:8000/ws/chat/",
        "ws://127.0.0.1:8000/ws/chat",
        "ws://localhost:8000/ws/chat/",
        "wss://127.0.0.1:8000/ws/chat/",
    ]

    for uri in urls:
        print(f"\nTrying to connect to {uri}...")
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Successfully connected to {uri}!")
                message = {
                    # "message": "What is the date and time now?"
                    "message": "what are some recent news from today"
                }

                await websocket.send(json.dumps(message))
                print("Message sent!")

                while True:
                    try:
                        response = await websocket.recv()
                        print(f"Received: {response}")
                    except websockets.ConnectionClosed:
                        print("Connection closed")
                        break
                # If we successfully connect, break the loop
                break
        except Exception as e:
            print(f"Failed to connect to {uri}: {str(e)}")
            continue


if __name__ == "__main__":
    asyncio.run(test_websocket())
