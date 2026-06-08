import os
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage

from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_supervisor(messages: List[BaseMessage], system_rules: str = "") -> Dict[str, Any]:
    """
    Analyzes the conversation state and decides the next agent.
    Routes to:
      - 'executor' for creating, updating, or editing plans/tasks.
      - 'retriever' for searching, listing, querying, or asking questions about plans.
      - 'rule_manager' for adding or deleting operational instructions or rules.
      - 'responder' if no database operation is needed (casual talk, simple greetings, or final answers).
    """
    # 1. Parse history to find last human message and the preceding user-facing AI message
    last_human_msg = ""
    prev_ai_msg = ""
    for msg in reversed(messages):
        if msg.type == "human" and not last_human_msg:
            last_human_msg = msg.content
        elif (msg.type == "ai" or getattr(msg, "role", "") == "assistant") and last_human_msg and not prev_ai_msg:
            cleaned = msg.content.strip()
            if not cleaned.startswith("[System"):
                prev_ai_msg = cleaned

    # 2. Check if this is a confirmation response to a task deletion request
    if last_human_msg and prev_ai_msg:
        confirm_words = ["delete", "confirm", "yes", "y", "ok", "go ahead", "do it"]
        last_lower = last_human_msg.lower().strip()
        if any(last_lower == cw or last_lower.startswith(cw + " ") for cw in confirm_words):
            prev_lower = prev_ai_msg.lower()
            if "delete" in prev_lower and "confirm" in prev_lower:
                return {
                    "next_agent": "executor",
                    "reason": "User confirmed task deletion request."
                }

    # 3. If a database tool has just finished execution, route directly to the responder to format the confirmation reply
    if messages and (messages[-1].type == "ai" or getattr(messages[-1], "role", "") == "assistant"):
        last_msg_content = messages[-1].content.strip()
        if last_msg_content.startswith("[System Executed]") or last_msg_content.startswith("[System Executed Error]"):
            return {
                "next_agent": "responder",
                "reason": "Database tool execution completed. Routing to responder to format the reply."
            }

    # If the last message is already a user-facing assistant message (not a system log), we are done.
    if messages and (messages[-1].type == "ai" or getattr(messages[-1], "role", "") == "assistant"):
        if not messages[-1].content.startswith("[System"):
            return {
                "next_agent": "FINISH",
                "reason": "Last message was a user-facing assistant response. Task is complete."
            }
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    
    system_prompt = (
        "You are the Supervisor agent for Project TaskMaker AI, a multi-agent terminal secretary.\n"
        "Your task is to analyze the conversation history and decide the next agent.\n"
        "You must respond in valid JSON format with the following keys:\n"
        '  "next_agent": string, must be one of "executor", "planner", "retriever", "responder", or "rule_manager"\n'
        '  "reason": string, brief explanation of your choice\n\n'
        "Routing guidelines:\n"
        "1. Route requests to ADD or CREATE a plan/task that is complex or has multiple sub-steps/decomposition (e.g. 'study biology', 'learn python', setting up a project, organizing an event) to the 'planner' agent.\n"
        "2. Route requests to MODIFY, UPDATE, EDIT, DELETE, or MARK AS COMPLETED tasks or plans, or requests to ADD a simple single-step task without subtasks, to the 'executor' agent.\n"
        "3. Route requests to SEARCH, FIND, QUERY, LIST, or SHOW plans in the database to the 'retriever' agent.\n"
        "4. Route operations that target AI behavioral rules, system preferences, or guidelines (e.g. 'Always prioritize work', 'Forget the rule about X', 'List all rules') to the 'rule_manager' agent.\n"
        "5. Route casual greeting, general chat, general question answering, or requests to display database operation confirmations to the 'responder' agent.\n\n"
        "Deletion Routing Rules:\n"
        "- If deleting rules, instructions, or preferences (e.g., 'delete rule X', 'remove guideline'), route to the 'rule_manager' agent.\n"
        "- If deleting tasks, plans, reminders, or general ambiguous deletions (e.g., 'delete', 'delete all', 'remove', 'clear'), route to the 'executor' agent. Do NOT route these to the rule_manager."
    )
    if system_rules:
        system_prompt += f"\nActive Operational Rules to follow:\n{system_rules}\n"
    
    # Provide system prompt and the last few messages for state tracking
    context_messages = [SystemMessage(content=system_prompt)]
    # Append up to 5 messages to avoid blowing up context
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
            
        data = json.loads(content)
        next_agent = data.get("next_agent", "responder")
        if next_agent not in ["executor", "planner", "retriever", "responder", "rule_manager"]:
            next_agent = "responder"
            
        # Programmatic check: if routed to executor or planner for an update/delete/refine request,
        # verify if we have already fetched the candidate tasks via vector search.
        if next_agent in ["executor", "planner"]:
            last_human_msg = ""
            for msg in reversed(messages):
                if msg.type == "human":
                    last_human_msg = msg.content
                    break
            
            query_lower = last_human_msg.lower()
            mutation_words = ["set", "update", "change", "modify", "edit", "delete", "remove", "cancel", "postpone", "reschedule", "alter", "status", "complete", "finish", "mark", "tick", "uncheck", "refine", "detail", "more steps", "more detailed", "add a step", "add steps"]
            is_mutation = any(word in query_lower for word in mutation_words)
            
            has_retrieved = False
            for msg in reversed(messages):
                if msg.type == "human":
                    break
                if msg.type == "ai" and msg.content.startswith("[System Retrieved]"):
                    has_retrieved = True
                    break
            
            if is_mutation and not has_retrieved:
                next_agent = "retriever"
                return {
                    "next_agent": "retriever",
                    "reason": "Rerouting to retriever first to run vector search for the target tasks."
                }
            
        return {
            "next_agent": next_agent,
            "reason": data.get("reason", "Parsed routing choice.")
        }
    except Exception as e:
        # Fallback to responder
        return {
            "next_agent": "responder",
            "reason": f"Routing fallback due to error: {str(e)}"
        }
