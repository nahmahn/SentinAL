import sys
import os
import asyncio
from contextlib import asynccontextmanager
import importlib.resources
import httpx
import uvicorn
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Ensure we can import aeternus
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeternus import Agent, Browser, ChatBrowserUse
from backend.finance_router import FinanceRouter, FinanceContext, INTENT_GENERIC
from backend.market_data import router as market_router
from backend.db import init_db, Transaction, db as sqlite_db

# Unique CDP port for Aeternus - must match electron/main.ts
AETERNUS_CDP_PORT = 9333

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(market_router)

class AgentRequest(BaseModel):
    task: str

@app.get("/api/transactions")
async def get_transactions():
    """Retrieve all transactions and agent activities from the database."""
    try:
        txs = Transaction.select().order_by(Transaction.timestamp.desc())
        return [{
            "id": tx.id,
            "title": tx.title,
            "category": tx.category,
            "description": tx.description,
            "amount": tx.amount,
            "status": tx.status,
            "icon": tx.icon,
            "timestamp": tx.timestamp.strftime("%Y-%m-%d %H:%M"),
            "is_positive": tx.is_positive,
            "source": tx.source
        } for tx in txs]
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return []

@app.get("/health")
def health():
    return {"status": "ok", "service": "Aeternus Agent", "cdp_port": AETERNUS_CDP_PORT}

async def verify_aeternus_connection() -> tuple[str | None, str | None]:
    """Verify we're connecting to the Aeternus Electron app and return the BrowserView's WebSocket URL.
    
    Returns:
        Tuple of (ws_url, error_message). One will be None.
        
    Validation checks:
    1. CDP endpoint is reachable
    2. There's at least one page target
    3. We can identify the BrowserView (the page showing actual web content)
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if CDP endpoint is reachable
            try:
                response = await client.get(f"http://localhost:{AETERNUS_CDP_PORT}/json/version")
                version_info = response.json()
                browser_name = version_info.get("Browser", "Unknown")
                
                # Verify it's Electron
                if "Electron" not in browser_name and "Chrome" not in browser_name:
                    return None, f"Unexpected browser: {browser_name}. Expected Electron."
                    
                print(f"[CDP] Connected to: {browser_name}")
            except Exception as e:
                return None, f"Cannot reach Aeternus on port {AETERNUS_CDP_PORT}. Is the app running?"
            
            # Get targets
            response = await client.get(f"http://localhost:{AETERNUS_CDP_PORT}/json")
            targets = response.json()
            
            if not targets:
                return None, "No browser targets found. The Aeternus app may not be fully loaded."
            
            # Find the BrowserView page (the one showing web content, not the React UI)
            # The BrowserView loads external URLs (like google.com)
            # The main window loads localhost:5173 (the React app)
            browser_view_target = None
            react_app_target = None
            
            for target in targets:
                if target.get("type") != "page" or "parentId" in target:
                    continue
                    
                url = target.get("url", "")
                title = target.get("title", "")
                
                # Skip internal pages
                if url.startswith("chrome://") or url.startswith("devtools://"):
                    continue
                
                # The React app runs on localhost:5173
                if "localhost:5173" in url or "localhost:5174" in url:
                    react_app_target = target
                    continue
                
                # This is likely the BrowserView (external web content)
                browser_view_target = target
                print(f"[CDP] Found BrowserView: '{title}' - {url[:50]}...")
            
            if browser_view_target:
                ws_url = browser_view_target.get("webSocketDebuggerUrl")
                return ws_url, None
            
            # If no BrowserView found but React app exists, the user hasn't navigated yet
            if react_app_target:
                return None, "BrowserView not ready. Please navigate to a webpage first."
            
            return None, "Could not find the Aeternus BrowserView target."
                
    except httpx.ConnectError:
        return None, f"Cannot connect to port {AETERNUS_CDP_PORT}. Make sure the Aeternus app is running."
    except Exception as e:
        return None, f"Connection error: {str(e)}"

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] UI Connected")
    
    active_agent = None
    agent_task = None

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            # --- Handle Human-in-the-Loop Responses ---
            if request.get("type") == "hitl_response":
                if active_agent and active_agent.state.paused:
                    action = request.get("action")
                    feedback = request.get("feedback", "")
                    
                    # Formulate human feedback
                    human_msg = f"Human Review Result: {action.upper()}"
                    if feedback:
                        human_msg += f". Feedback: {feedback}"
                    
                    logger.info(f"👤 Human responded: {human_msg}")
                    
                    # Inject the response into the agent's recent result so it learns the human's decision
                    from aeternus.agent.views import ActionResult
                    active_agent.state.last_result = [
                        ActionResult(is_done=False, extracted_content=human_msg, long_term_memory=human_msg)
                    ]
                    
                    if action == "reject":
                        # If rejected, we might want to tell the agent to stop or just let it read the rejection.
                        # Setting consecutive failures will encourage it to halt if it tries again, but better to let it see the reject msg.
                        pass
                        
                    # Resume execution
                    active_agent.resume()
                    await websocket.send_json({"type": "info", "message": f"Agent resumed after human {action}."})
                else:
                    await websocket.send_json({"type": "error", "message": "Agent is not currently paused for review."})
                continue
                
            # --- Handle New Tasks ---
            task = request.get("task")
            if not task:
                continue
                
            await websocket.send_json({"type": "info", "message": f"Received: {task}"})
            
            # Define the agent execution flow as a separate async function to run non-blocking
            async def execute_agent(task_prompt: str):
                nonlocal active_agent
                try:
                    # Verify connection to Aeternus and get WebSocket URL
                    ws_url, error = await verify_aeternus_connection()
                    
                    if error:
                        await websocket.send_json({"type": "error", "message": error})
                        return
                    
                    await websocket.send_json({"type": "info", "message": "Connected to browser"})
                    
                    # Connect to the verified BrowserView
                    browser = Browser(cdp_url=ws_url)
                    llm = ChatBrowserUse()

                    # ─── Finance Classification ───────────────────────
                    finance_router = FinanceRouter(llm=llm)
                    finance_context = await finance_router.classify(task_prompt)
                    
                    if finance_context.is_financial:
                        await websocket.send_json({
                            "type": "finance_context",
                            "message": f"🏦 Financial task detected: {finance_context.intent} | Risk: {finance_context.risk_level}",
                            "data": {
                                "intent": finance_context.intent,
                                "risk_level": finance_context.risk_level,
                                "estimated_amount": finance_context.estimated_amount,
                                "is_irreversible": finance_context.is_irreversible,
                                "paytm_detected": finance_context.paytm_detected,
                            }
                        })
                        logger.info(f"🏦 Finance context: {finance_context.intent} | Risk: {finance_context.risk_level}")

                    # ─── Build extend_system_message with finance prompt ─
                    extend_system_message = None
                    if finance_context.is_financial:
                        try:
                            finance_prompt_path = (
                                importlib.resources.files('aeternus.agent.system_prompts')
                                .joinpath('finance_system.md')
                            )
                            with finance_prompt_path.open('r', encoding='utf-8') as f:
                                finance_prompt = f.read()
                            
                            extend_system_message = (
                                f"\n\n{finance_context.to_prompt_context()}\n\n"
                                f"{finance_prompt}"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to load finance system prompt: {e}")

                    # Define step callback for real-time updates and HITL triggers
                    async def on_step(browser_state, model_output, step_number):
                        try:
                            # Send thought process
                            if hasattr(model_output, 'thinking') and model_output.thinking:
                                await websocket.send_json({"type": "thought", "message": model_output.thinking})
                            
                            # Check for High-Risk HITL triggering actions
                            if hasattr(model_output, 'action') and model_output.action:
                                for action_item in model_output.action:
                                    action_data = action_item.model_dump(exclude_unset=True) if hasattr(action_item, 'model_dump') else action_item
                                    action_name = next(iter(action_data.keys())) if action_data else 'unknown'
                                    
                                    # Trigger HITL if agent uses ask_human or flag_suspicious_field
                                    if action_name in ["ask_human", "flag_suspicious_field"]:
                                        params = action_data[action_name]
                                        reason = params.get("reason", "Please review this action before proceeding.")
                                        await websocket.send_json({
                                            "type": "hitl_request",
                                            "message": "Human approval required",
                                            "reason": reason,
                                            "action_name": action_name
                                        })
                                        if active_agent:
                                            # Pause the agent execution until human responds
                                            active_agent.pause()
                            
                            await websocket.send_json({
                                "type": "step", 
                                "step": step_number,
                                "url": browser_state.url if hasattr(browser_state, 'url') else None
                            })
                        except Exception as step_e:
                            print(f"[Agent] Error in step callback: {step_e}")

                    # ─── Create Agent ────────────
                    agent = Agent(
                        task=task_prompt,
                        llm=llm,
                        browser=browser,
                        max_actions_per_step=10,
                        register_new_step_callback=on_step,
                        extend_system_message=extend_system_message,
                    )
                    active_agent = agent

                    # Register finance tools if task is financial
                    if finance_context.is_financial:
                        try:
                            from aeternus.tools.finance_tools import register_finance_tools
                            register_finance_tools(agent.tools)
                            agent._setup_action_models()
                        except Exception as e:
                            logger.warning(f"Failed to register finance tools: {e}")
                    
                    await websocket.send_json({"type": "info", "message": "Agent running..."})
                    
                    Transaction.create(
                        title=f"Task: {task_prompt[:30]}...",
                        category="Intelligence",
                        description=f"Agent started task: {task_prompt}",
                        status="Pending",
                        icon="psychology",
                        source="Agent"
                    )
                    
                    history = await agent.run()
                    result_text = history.final_result() if hasattr(history, 'final_result') else str(history)
                    
                    try:
                        last_tx = Transaction.select().order_by(Transaction.id.desc()).get()
                        last_tx.status = "Completed"
                        last_tx.description += f"\nResult: {result_text[:100]}"
                        last_tx.save()
                    except:
                        pass

                    await websocket.send_json({"type": "success", "message": f"Done: {result_text}"})
                    await websocket.send_json({"type": "done", "result": result_text})

                except Exception as e:
                    print(f"[Agent] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        await websocket.send_json({"type": "error", "message": str(e)})
                    except:
                        pass
                finally:
                    active_agent = None

            # Spawn the agent execution as a background task to free up the websocket reader
            agent_task = asyncio.create_task(execute_agent(task))

    except WebSocketDisconnect:
        print("[WS] Client disconnected")

if __name__ == "__main__":
    print(f"[Aeternus Backend] Starting on port 8000, expecting CDP on port {AETERNUS_CDP_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
