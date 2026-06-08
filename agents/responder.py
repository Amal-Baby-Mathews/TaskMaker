import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage

from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_responder(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a final user-facing response.
    - If a task was recently added or updated (e.g. system log exists), summarizes it nicely.
    - Otherwise, provides a polite response to user greetings/questions.
    """
    messages = state.get("messages", [])
    
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0.7
    )
    
    system_rules = state.get("system_rules", "")
    system_prompt = (
        "You are the friendly secretary assistant for Project TaskMaker AI.\n"
        "Your task is to reply to the user or summarize the recent database actions in a polite, helpful way.\n"
        "If a database operation was executed (indicated by '[System Executed]' in the history), "
        "translate it into a user-friendly confirmation (e.g. 'I have created that task for you.').\n"
        "CRITICAL: If the database operation failed (indicated by '[System Executed Error]' in the history), "
        "you MUST inform the user of the failure and explain what failed (e.g. 'I tried to update the task but could not find a match.'). Do NOT pretend it succeeded.\n"
        "If the user is saying hello, greeting, or chatting, respond warmly and ask how you can help."
    )
    if system_rules:
        system_prompt += f"\nActive Operational Rules to follow:\n{system_rules}\n"
        
    context_messages = [SystemMessage(content=system_prompt)]
    # Limit context to the last 5 messages for brevity and speed
    for msg in messages[-5:]:
        context_messages.append(msg)
        
    try:
        response = llm.invoke(context_messages)
        content = response.content.strip()
        
        new_messages = list(messages)
        new_messages.append(AIMessage(content=content))
        
        return {
            "messages": new_messages,
            "next_agent": "FINISH"
        }
    except Exception as e:
        error_msg = f"[Responder Error] Failed to generate response: {str(e)}"
        new_messages = list(messages)
        new_messages.append(AIMessage(content=error_msg))
        return {
            "messages": new_messages,
            "next_agent": "FINISH"
        }
