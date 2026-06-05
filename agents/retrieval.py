import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from tools.db_tools import query_plans

from tools.config_loader import load_config

# Load configuration from config.json / environments
cfg = load_config()
LLM_BASE_URL = cfg["LLM_BASE_URL"]
LLM_API_KEY = cfg["LLM_API_KEY"]
LLM_MODEL = cfg["LLM_MODEL"]

def run_retriever(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs vector memory/RAG lookup using the ChromaDB query tool,
    and returns a summarized, natural language response.
    """
    messages = state.get("messages", [])
    
    # Extract query from the last user message
    last_user_query = ""
    for msg in reversed(messages):
        if msg.type == "human":
            last_user_query = msg.content
            break
            
    # Retrieve matching plans
    retrieved_plans = query_plans(last_user_query, limit=5)
    
    # Generate RAG response
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=0.7
    )
    
    system_rules = state.get("system_rules", "")
    system_prompt = (
        "You are the Retrieval Agent for Project TaskMaker AI.\n"
        "You perform Retrieval-Augmented Generation (RAG) using plans retrieved from ChromaDB.\n"
        "Generate a natural, helpful assistant response answering the user's query.\n"
        "If there are matching plans below, summarize them clearly.\n"
        "If no plans match or the list is empty, state clearly that no plans were found.\n\n"
    )
    if system_rules:
        system_prompt += f"Active Operational Rules to follow:\n{system_rules}\n\n"
        
    system_prompt += f"Retrieved Plans:\n{retrieved_plans}\n"
    
    context_messages = [SystemMessage(content=system_prompt)]
    for msg in messages[-5:]:
        context_messages.append(msg)
        
    try:
        response = llm.invoke(context_messages)
        content = response.content
        
        new_messages = list(messages)
        new_messages.append(AIMessage(content=content))
        
        return {
            "messages": new_messages,
            "next_agent": "supervisor"
        }
    except Exception as e:
        error_msg = f"[Retrieval Error] Failed to generate RAG response: {str(e)}"
        new_messages = list(messages)
        new_messages.append(AIMessage(content=error_msg))
        return {
            "messages": new_messages,
            "next_agent": "supervisor"
        }
