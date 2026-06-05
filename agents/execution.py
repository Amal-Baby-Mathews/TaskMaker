import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from tools.db_tools import add_plan, update_plan, delete_plan, create_repeating_plan
from tools.info_tools import get_current_datetime

from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_executor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles CRUD operations on ChromaDB.
    - If task_payload has validated=True, invokes database tool.
    - If task_payload is empty or contains errors, generates or fixes the JSON payload using LLM.
    """
    messages = state.get("messages", [])
    task_payload = state.get("task_payload", {}) or {}
    
    # Check if the payload has already been validated by the Critic Agent
    if task_payload.get("validated") is True:
        tasks = task_payload.get("tasks", [])
        executed_messages = []
        for task in tasks:
            action = task.get("action")
            plan_id = task.get("plan_id")
            title = task.get("title")
            description = task.get("description")
            due_time = task.get("due_time")
            status = task.get("status", "pending")
            
            try:
                if action == "create":
                    actual_id = add_plan(
                        plan_id=plan_id,
                        title=title,
                        description=description,
                        due_time=due_time,
                        status=status
                    )
                    executed_messages.append(f"[System Executed] Created plan '{title}' (ID: {actual_id}) due at {due_time}.")
                elif action == "update":
                    update_plan(
                        plan_id=plan_id,
                        title=title,
                        description=description,
                        due_time=due_time,
                        status=status
                    )
                    executed_messages.append(f"[System Executed] Updated plan (ID: {plan_id}).")
                elif action == "delete":
                    deleted_ids = delete_plan(plan_id=plan_id)
                    if deleted_ids:
                        executed_messages.append(f"[System Executed] Deleted plan(s): {', '.join(deleted_ids)}.")
                    else:
                        executed_messages.append(f"[System Executed] No plans matching '{plan_id}' were found to delete.")
                elif action == "create_repeating":
                    freq = task.get("frequency", "daily")
                    rep = task.get("repeat_count", 7)
                    created_ids = create_repeating_plan(
                        plan_id=plan_id,
                        title=title,
                        description=description,
                        start_time=due_time,
                        frequency=freq,
                        count=rep,
                        status=status
                    )
                    executed_messages.append(f"[System Executed] Created repeating plans ({rep} occurrences): {', '.join(created_ids)}.")
                else:
                    executed_messages.append(f"[System Executed] Unrecognized action: {action}")
            except Exception as e:
                executed_messages.append(f"[System Executed Error] Failed to execute DB tool: {str(e)}")
                
        success_msg = "\n".join(executed_messages)
        new_messages = list(messages)
        new_messages.append(AIMessage(content=success_msg))
        
        return {
            "messages": new_messages,
            "task_payload": {},  # Clear payload after execution
            "next_agent": "supervisor"
        }
        
    # Extract or fix payload
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    
    system_rules = state.get("system_rules", "")
    has_errors = "errors" in task_payload
    errors_info = task_payload.get("errors", "")
    
    current_time_info = get_current_datetime()
    system_prompt = (
        "You are the Execution Agent for Project TaskMaker AI. Your job is to extract task parameters "
        "from the conversation history and output them in a strict JSON format.\n\n"
        f"CRITICAL: The current datetime is {current_time_info}. You MUST refer to this current "
        "datetime when resolving relative date/times (like 'tomorrow', 'Friday', 'next week') "
        "and record the resolved absolute date/time in the 'due_time' field of the task payload.\n\n"
    )
    if system_rules:
        system_prompt += f"Active Operational Rules to follow:\n{system_rules}\n\n"
        
    system_prompt += (
        "Output JSON format:\n"
        "{\n"
        '  "tasks": [\n'
        "    {\n"
        '      "action": "create", "update", "delete", or "create_repeating",\n'
        '      "plan_id": "string",\n'
        '      "title": "string" (optional, required if action is create or create_repeating),\n'
        '      "description": "string" (optional, required if action is create or create_repeating),\n'
        '      "due_time": "string" (optional, required if action is create or create_repeating. Acts as start time for repeating tasks),\n'
        '      "status": "string" (optional),\n'
        '      "frequency": "daily" or "weekly" (optional, for create_repeating),\n'
        '      "repeat_count": integer (optional, for create_repeating)\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Instructions:\n"
        "1. For 'create': Generate a short, unique plan_id (e.g. plan_001, plan_002) if none is provided. Ensure they are distinct for each task.\n"
        "2. For 'update': Identify the plan_id from context. Only include fields that the update explicitly targets.\n"
        "3. For 'delete': Identify the plan_id from context. Set action to 'delete'.\n"
        "   - If deleting a specific plan, provide its plan_id.\n"
        "   - If deleting ALL reminders, set plan_id to 'all'.\n"
        "   - If deleting reminders matching a keyword/item (e.g. 'cherry', 'fruit', 'meeting'), set plan_id to 'query:<keyword>' (e.g. 'query:cherry').\n"
        "4. For 'create_repeating': Use this action when a user requests a task to repeat periodically (e.g. 'everyday starting tomorrow at 8 am for next week' or 'every Monday'). Set 'frequency' to 'daily' or 'weekly' and 'repeat_count' to the number of occurrences requested (default: 7). Provide a base plan_id (e.g. 'plan_024') which will be used to generate sub-IDs (e.g. 'plan_024_1', 'plan_024_2').\n"
        "5. Support multiple tasks creation/deletion: If the user describes operations on multiple tasks, generate a list containing all distinct task dicts in the 'tasks' array.\n"
        "6. Sequential Date/Time Incrementing: If the user requests assigning multiple tasks to separate consecutive days or times, you MUST increment the due_time sequentially for each task (e.g., Task 1: 2026-06-02, Task 2: 2026-06-03, Task 3: 2026-06-04, etc.) rather than setting them all to the same day."
    )
    
    if has_errors:
        system_prompt += (
            f"\nWARNING: Your previous payload failed validation with error:\n'{errors_info}'\n"
            "Please fix the payload by making sure all required fields are present and valid."
        )
        
    context_messages = [SystemMessage(content=system_prompt)]
    for msg in messages[-5:]:
        context_messages.append(msg)
        
    if has_errors:
        context_messages.append(SystemMessage(content=f"Previous Faulty Payload: {json.dumps(task_payload)}"))
        
    try:
        response = llm.invoke(context_messages)
        content = response.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        new_payload = json.loads(content)
        new_payload["validated"] = False  # Mark for validation
        
        return {
            "task_payload": new_payload,
            "next_agent": "critic"
        }
    except Exception as e:
        # Fallback payload with error info to critic
        fallback_payload = dict(task_payload)
        fallback_payload["validated"] = False
        fallback_payload["errors"] = f"Failed to extract JSON parameters: {str(e)}"
        return {
            "task_payload": fallback_payload,
            "next_agent": "critic"
        }
