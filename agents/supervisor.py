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
        '  "next_agent": string, must be one of "executor", "retriever", "responder", or "rule_manager"\n'
        '  "reason": string, brief explanation of your choice\n\n'
        "Routing guidelines:\n"
        "1. If the user wants to ADD, CREATE, UPDATE, MODIFY, EDIT, or DELETE a plan/task, set next_agent to 'executor'.\n"
        "2. If the user wants to SEARCH, FIND, QUERY, LIST, SHOW plans, or asks questions about plans in DB, set next_agent to 'retriever'.\n"
        "3. If the user wants to ADD, CREATE, DELETE, LIST, or CLEAR system preferences, operational rules, or instructions (e.g. 'Always prioritize X', 'Forget rule about Y', 'List all rules'), set next_agent to 'rule_manager'.\n"
        "4. If the user is greeting, chatting, asking a general question, or if a database operation was just executed and we need to show a confirmation response to the user, set next_agent to 'responder'.\n"
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
        if next_agent not in ["executor", "retriever", "responder", "rule_manager"]:
            next_agent = "responder"
            
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
