import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage
from tools.info_tools import get_current_datetime
from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_planner(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decomposes a complex task into a set of subtasks.
    Integrates retrieved system rules/preferences to structure the subtask list.
    Outputs the compiled payload to `task_payload` and routes to `critic`.
    """
    messages = state.get("messages", [])
    system_rules = state.get("system_rules", "")
    
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    
    current_time_info = get_current_datetime()
    
    system_prompt = (
        "You are the Planner Agent for Project TaskMaker AI. Your job is to analyze a complex request, "
        "determine the parent task parameters, and decompose it into a clean list of subtasks.\n\n"
        f"CRITICAL: The current datetime is {current_time_info}. You MUST refer to this current "
        "datetime when resolving relative date/times (like 'tomorrow', 'Friday', 'next week') "
        "and record the resolved absolute date/time in the 'due_time' field of the task payload.\n\n"
    )
    
    if system_rules:
        system_prompt += f"Active Operational Rules / Preferences to guide your planning:\n{system_rules}\n\n"
        
    system_prompt += (
        "You must output valid JSON format with the following keys:\n"
        "{\n"
        '  "tasks": [\n'
        "    {\n"
        '      "action": "create" or "update",\n'
        '      "plan_id": "string" (For action "create": generate a unique ID like plan_001, plan_002. For action "update": look for the most relevant existing plan from context history or retrieved tasks, and use its exact plan_id),\n'
        '      "title": "string" (parent task title),\n'
        '      "description": "string" (parent task description),\n'
        '      "due_time": "string" (resolved due date/time format YYYY-MM-DD HH:MM:SS),\n'
        '      "status": "pending" or "completed" or "in_progress",\n'
        '      "subtasks": [\n'
        "        {\n"
        '          "id": "1",\n'
        '          "title": "string" (actionable subtask description),\n'
        '          "completed": false\n'
        "        },\n"
        "        {\n"
        '          "id": "2",\n'
        '          "title": "string" (next subtask description),\n'
        '          "completed": false\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Instructions:\n"
        "1. Identify the parent task the user wants to schedule or update/refine.\n"
        "2. Break down the task into 3-8 logical, progressive steps/subtasks. If updating/detailing an existing plan, decompose it into a new, more detailed/refined set of subtasks.\n"
        "3. Use the retrieved active operational rules / preferences to shape these subtasks.\n"
        "4. Determining the action and plan_id:\n"
        "   - If the user request is modifying, detailing, refining, or updating an existing task/plan (look for mentions of existing tasks in the history, such as '[System Executed] Created plan ... (ID: plan_XXX)' or '[System Retrieved] Matching tasks from database: ...'), set 'action' to 'update' and set 'plan_id' to that exact plan's ID.\n"
        "   - Otherwise (creating a new plan), set 'action' to 'create' and generate a new plan_id."
    )
    
    context_messages = [SystemMessage(content=system_prompt)]
    # Limit context to the last 5 messages for speed/context windows
    for msg in messages[-5:]:
        context_messages.append(msg)
        
    try:
        response = llm.invoke(context_messages)
        content = response.content.strip()
        
        # Strip markdown syntax if LLM returns it
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        task_payload = json.loads(content)
        task_payload["validated"] = False  # Mark for validation by critic
        
        return {
            "task_payload": task_payload,
            "next_agent": "critic"
        }
    except Exception as e:
        # Fallback payload
        fallback_payload = {
            "tasks": [],
            "validated": False,
            "errors": f"Planner failed to decompose task: {str(e)}"
        }
        return {
            "task_payload": fallback_payload,
            "next_agent": "critic"
        }
