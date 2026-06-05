import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from tools.db_tools import add_rule, delete_rule, get_all_rules
from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_rule_manager(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles CRUD operations on system_rules ChromaDB collection.
    Extracts rule operations from user query and runs the db tools.
    """
    messages = state.get("messages", [])
    
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    
    system_prompt = (
        "You are the Rule Manager agent for Project TaskMaker AI.\n"
        "Your task is to analyze the user query and extract rule-related actions.\n"
        "You must respond in valid JSON format with the following schema:\n"
        "{\n"
        '  "actions": [\n'
        "    {\n"
        '      "action": "create" | "delete" | "list",\n'
        '      "rule_id": string (required for delete, e.g. "rule_001" or "all" or search term like "X"),\n'
        '      "content": string (required for create, e.g. "Always prioritize work tasks")\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Example inputs:\n"
        "- 'Add a rule that I should always prioritize work tasks':\n"
        '  {"actions": [{"action": "create", "rule_id": "rule_001", "content": "Always prioritize work tasks"}]}\n'
        "- 'Forget the rule about X':\n"
        '  {"actions": [{"action": "delete", "rule_id": "X"}]}\n'
        "- 'Delete all instructions':\n"
        '  {"actions": [{"action": "delete", "rule_id": "all"}]}\n'
        "- 'List all system rules':\n"
        '  {"actions": [{"action": "list"}]}\n'
    )
    
    context_messages = [SystemMessage(content=system_prompt)]
    # Append the last few user/assistant messages for context
    for msg in messages[-5:]:
        context_messages.append(msg)
        
    try:
        response = llm.invoke(context_messages)
        content = response.content.strip()
        
        # Strip markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        actions = data.get("actions", [])
        
        executed_messages = []
        for act in actions:
            action = act.get("action")
            rule_id = act.get("rule_id", "rule_001")
            rule_content = act.get("content", "")
            
            if action == "create":
                # Ensure we have a default prefix for rule IDs
                if not rule_id or not rule_id.startswith("rule_"):
                    rule_id = "rule_001"
                actual_id = add_rule(rule_id=rule_id, content=rule_content)
                executed_messages.append(f"[System Executed] Created system rule '{rule_content}' (ID: {actual_id}).")
            elif action == "delete":
                # Look up matches if it's a search term rather than a specific ID
                deleted_ids = []
                all_rules = get_all_rules()
                if rule_id == "all":
                    deleted_ids = delete_rule("all")
                else:
                    # Check for exact ID match first
                    exact_match = [r for r in all_rules if r["rule_id"] == rule_id]
                    if exact_match:
                        deleted_ids = delete_rule(rule_id)
                    else:
                        # Fallback: substring match in content or ID
                        matched = [r for r in all_rules if rule_id.lower() in r["content"].lower() or rule_id.lower() in r["rule_id"].lower()]
                        for m in matched:
                            deleted_ids.extend(delete_rule(m["rule_id"]))
                if deleted_ids:
                    executed_messages.append(f"[System Executed] Deleted rule(s): {', '.join(deleted_ids)}.")
                else:
                    executed_messages.append(f"[System Executed] No rules matching '{rule_id}' were found to delete.")
            elif action == "list":
                all_rules = get_all_rules()
                if all_rules:
                    rules_str = "\n".join([f"- {r['rule_id']}: {r['content']}" for r in all_rules])
                    executed_messages.append(f"[System Executed] Current system rules:\n{rules_str}")
                else:
                    executed_messages.append("[System Executed] There are no active system rules.")
                    
        if not executed_messages:
            executed_messages.append("[System Executed] No rule action was processed.")
            
        success_msg = "\n".join(executed_messages)
        new_messages = list(messages)
        new_messages.append(AIMessage(content=success_msg))
        
        return {
            "messages": new_messages,
            "task_payload": {},
            "next_agent": "supervisor"
        }
        
    except Exception as e:
        new_messages = list(messages)
        new_messages.append(AIMessage(content=f"[System Executed Error] Rule management error: {str(e)}"))
        return {
            "messages": new_messages,
            "task_payload": {},
            "next_agent": "supervisor"
        }
