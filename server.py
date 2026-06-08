"""
server.py — FastAPI backend for TaskMaker AI
Replaces the Streamlit UI layer (app.py) as the HTTP/SSE interface.
The LangGraph agent network, ChromaDB tools, and config remain untouched.

Run with:
    uvicorn server:app --reload --port 8000
"""

import os
import sys
import re
import json
import asyncio
import logging
from typing import Optional, List, Any

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from graph import app as graph_app
from tools.db_tools import (
    get_all_plans, update_plan, delete_plan,
    get_all_rules, add_rule, delete_rule, query_rules,
    save_chat_history, load_chat_history, clear_chat_history,
)
from tools.config_loader import load_config
from tools.logger import reset_log

reset_log()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("taskmaker.server")

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="TaskMaker AI API",
    description="REST + SSE interface for the TaskMaker multi-agent system",
    version="2.0.0",
)

@app.on_event("startup")
def startup_event():
    reset_log()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",   # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def clean_response(text: str) -> str:
    """Strip <think>...</think> reasoning blocks from model output."""
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in text:
        text = text.split("<think>")[0]
    return text.strip()


def _deserialize_history(raw: List[dict]) -> List[Any]:
    """Convert plain dicts from the client back to LangChain message objects."""
    messages = []
    for item in raw:
        role = item.get("role", "")
        content = item.get("content", "")
        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
    return messages


def _serialize_history(messages: List[Any]) -> List[dict]:
    """Convert LangChain message objects to plain dicts for JSON serialisation."""
    out = []
    for msg in messages:
        if msg.type in ("human", "ai", "system"):
            cleaned = clean_response(msg.content) if msg.type == "ai" else msg.content
            # Skip [System ...] internal DB-log messages from the response
            if msg.type == "ai" and cleaned.startswith("[System"):
                continue
            out.append({"role": msg.type, "content": cleaned})
    return out

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str         # "human" | "ai" | "system"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_time: Optional[str] = None
    status: Optional[str] = None
    subtasks: Optional[str] = None

class RuleCreateRequest(BaseModel):
    rule_id: Optional[str] = None
    content: str

# ---------------------------------------------------------------------------
# Health check & Streamlit compatibility mocks
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "TaskMaker AI"}


@app.get("/_stcore/health", include_in_schema=False)
async def streamlit_health():
    return "ok"


@app.get("/_stcore/host-config", include_in_schema=False)
async def streamlit_host_config():
    return {"allowedOrigins": []}

# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------

@app.get("/api/chat/history", tags=["chat"])
async def get_chat_history():
    """Return the persisted chat history as a JSON array."""
    try:
        messages = load_chat_history()
        return {"messages": _serialize_history(messages)}
    except Exception as exc:
        logger.exception("Failed to load chat history")
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/chat/history", tags=["chat"])
async def delete_chat_history():
    """Clear all persisted chat history."""
    try:
        clear_chat_history()
        return {"ok": True}
    except Exception as exc:
        logger.exception("Failed to clear chat history")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat/stream", tags=["chat"])
async def stream_chat(body: ChatRequest):
    """
    Run the LangGraph agent network and stream SSE events back to the client.

    SSE event shapes:
        {"event": "node_active", "node": "<agent_name>"}
        {"event": "node_idle",   "node": "<agent_name>"}
        {"event": "message",     "content": "<final reply>"}
        {"event": "done"}
        {"event": "error",       "detail": "<message>"}
    """

    async def event_generator():
        # Rebuild full history from client payload
        lc_history = _deserialize_history([m.model_dump() for m in body.history])
        lc_history.append(HumanMessage(content=body.message))

        # Inject semantically relevant system rules
        relevant_rules = query_rules(body.message, limit=5)
        system_rules_str = "\n".join([f"- {r['content']}" for r in relevant_rules]) if relevant_rules else ""

        state = {
            "messages": lc_history,
            "task_payload": {},
            "next_agent": "supervisor",
            "system_rules": system_rules_str,
        }

        valid_nodes = {"supervisor", "executor", "critic", "retriever", "responder", "rule_manager", "planner"}

        try:
            async for event in graph_app.astream_events(state, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name")

                if event_type == "on_chain_start" and event_name in valid_nodes:
                    payload = json.dumps({"event": "node_active", "node": event_name})
                    yield f"data: {payload}\n\n"
                    await asyncio.sleep(0)  # yield control to event loop

                elif event_type == "on_chain_end" and (event_name in valid_nodes or event_name == "LangGraph"):
                    if event_name in valid_nodes:
                        payload = json.dumps({"event": "node_idle", "node": event_name})
                        yield f"data: {payload}\n\n"

                    node_output = event.get("data", {}).get("output")
                    if node_output and isinstance(node_output, dict):
                        if "messages" in node_output:
                            state["messages"] = node_output["messages"]
                        if "task_payload" in node_output:
                            state["task_payload"] = node_output["task_payload"]

                    # On full graph completion emit the final assistant message
                    if event_name == "LangGraph":
                        messages = state.get("messages", [])
                        final_msg = None
                        for msg in reversed(messages):
                            if msg.type == "ai":
                                cleaned = clean_response(msg.content)
                                if cleaned and not cleaned.startswith("[System"):
                                    final_msg = cleaned
                                    break

                        if final_msg:
                            payload = json.dumps({"event": "message", "content": final_msg})
                            yield f"data: {payload}\n\n"

                        # Persist updated history
                        try:
                            save_chat_history(state["messages"])
                        except Exception:
                            logger.warning("Could not persist chat history after stream")

                        yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as exc:
            logger.exception("Error during agent stream")
            payload = json.dumps({"event": "error", "detail": str(exc)})
            yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if proxied
        },
    )

# ---------------------------------------------------------------------------
# Task (plan) endpoints
# ---------------------------------------------------------------------------

@app.get("/api/tasks", tags=["tasks"])
async def list_tasks():
    """Return all plans stored in ChromaDB."""
    try:
        plans = get_all_plans()
        return {"plans": plans}
    except Exception as exc:
        logger.exception("Failed to retrieve tasks")
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/api/tasks/{plan_id}", tags=["tasks"])
async def update_task(plan_id: str, body: TaskUpdateRequest):
    """Update title, description, and/or status of an existing task."""
    try:
        update_plan(
            plan_id=plan_id,
            title=body.title,
            description=body.description,
            due_time=body.due_time,
            status=body.status,
            subtasks=body.subtasks,
        )
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to update task %s", plan_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/tasks/{plan_id}", tags=["tasks"])
async def remove_task(plan_id: str):
    """Delete a specific task by its plan_id."""
    try:
        deleted = delete_plan(plan_id)
        return {"ok": True, "deleted": deleted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to delete task %s", plan_id)
        raise HTTPException(status_code=500, detail=str(exc))

# ---------------------------------------------------------------------------
# Rules endpoints
# ---------------------------------------------------------------------------

@app.get("/api/rules", tags=["rules"])
async def list_rules():
    """Return all operational rules stored in ChromaDB."""
    try:
        rules = get_all_rules()
        return {"rules": rules}
    except Exception as exc:
        logger.exception("Failed to retrieve rules")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/rules", tags=["rules"])
async def create_rule(body: RuleCreateRequest):
    """Add a new operational instruction/rule."""
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Rule content cannot be empty.")
    try:
        assigned_id = body.rule_id.strip() if body.rule_id and body.rule_id.strip() else "rule_001"
        final_id = add_rule(rule_id=assigned_id, content=body.content.strip())
        return {"ok": True, "rule_id": final_id}
    except Exception as exc:
        logger.exception("Failed to add rule")
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/rules/{rule_id}", tags=["rules"])
async def remove_rule(rule_id: str):
    """Delete a specific rule by its rule_id."""
    try:
        deleted = delete_rule(rule_id)
        return {"ok": True, "deleted": deleted}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to delete rule %s", rule_id)
        raise HTTPException(status_code=500, detail=str(exc))
