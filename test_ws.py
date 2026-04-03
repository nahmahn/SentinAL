import asyncio
import websockets
import json

async def test_hitl():
    uri = "ws://localhost:8000/ws/agent"
    events = []
    async with websockets.connect(uri) as websocket:
        task = "Process a financial transaction: send $500 to user via Paytm. Please use the ask_human tool with a question and reason before processing it."
        events.append(f"Sending task: {task}")
        await websocket.send(json.dumps({"task": task}))
        
        while True:
            try:
                response_str = await websocket.recv()
                response = json.loads(response_str)
                events.append(f"Received type: {response.get('type')}")
                
                if response.get("type") == "hitl_request":
                    events.append(f"HITL REQUEST: {response}")
                    events.append("Sending approval...")
                    await websocket.send(json.dumps({
                        "type": "hitl_response",
                        "action": "approve",
                        "feedback": "Yes, please proceed."
                    }))
                    events.append("Approval sent.")
                    
                elif response.get("type") in ["done", "error"]:
                    events.append(f"Final output: {response}")
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                events.append("Connection closed")
                break
                
    with open("test_events.json", "w") as f:
        json.dump(events, f, indent=2)

if __name__ == "__main__":
    asyncio.run(test_hitl())
