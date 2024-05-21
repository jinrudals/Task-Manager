import asyncio
import aioconsole
import websockets
import os
import json


async def receive_message(websocket, send_task, task_list):
    async for message in websocket:
        print(f"\nReceived message from server: {message}")
        if message == "TERMINATE":
            print("Terminate message received. Waiting for tasks to complete...")
            send_task.cancel()
            await websocket.close()
            break
        else:
            new_task_instance = asyncio.create_task(new_task(message))
            task_list.append(new_task_instance)


async def async_isfile(path):
    return await asyncio.to_thread(os.path.isfile, path)


async def new_task(filename):
    print("New task is added")
    try:
        while not await async_isfile(filename):
            await asyncio.sleep(1)  # Avoid busy-waiting
    except asyncio.CancelledError:
        print("New task was cancelled.")
    else:
        print(f"File {filename} detected.")
    finally:
        print("New task completed.")


async def send_message(websocket):
    try:
        while True:
            message = await aioconsole.ainput("Enter message to send to server: ")
            if message == "add":
                await websocket.send(json.dumps(
                    {
                        "action": "add",
                        "owner": await aioconsole.ainput("Owner : "),
                        "project": await aioconsole.ainput("Project : "),
                        "command": await aioconsole.ainput("Command : "),
                        "Timeout": await aioconsole.ainput("timeout : "),
                        "build": await aioconsole.ainput("build : ")
                    }
                ))
            if message == "complete":
                await websocket.send(json.dumps({
                    "action": "complete",
                    "project": await aioconsole.ainput("Project : "),
                    "command": await aioconsole.ainput("Command : "),
                    "Timeout": await aioconsole.ainput("timeout : "),
                    "build": await aioconsole.ainput("build : ")
                }))
                # await websocket.send(message)
    except asyncio.CancelledError:
        print("Send task cancelled.")


async def main(channel):
    uri = f"ws://127.0.1.1:8023/{channel}"
    print(f"Trying to connect to channel: {uri}")
    task_list = []

    try:
        async with websockets.connect(uri, timeout=10) as websocket:
            send_task = asyncio.create_task(send_message(websocket))
            receive_task = asyncio.create_task(
                receive_message(websocket, send_task, task_list))

            try:
                await asyncio.gather(receive_task, send_task)
            except asyncio.CancelledError:
                print("Tasks were cancelled. Exiting...")
            finally:
                await asyncio.gather(*task_list, return_exceptions=True)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Closing WebSocket connection...")

if __name__ == "__main__":
    channel = "temp"
    try:
        asyncio.run(main(channel))
    except KeyboardInterrupt:
        print("Script terminated by user.")
