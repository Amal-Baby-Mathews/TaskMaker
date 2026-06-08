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
            
    # Determine if this is a mutation request (update/delete/refinement)
    import json
    query_lower = last_user_query.lower()
    mutation_words = ["set", "update", "change", "modify", "edit", "delete", "remove", "cancel", "postpone", "reschedule", "alter", "status", "complete", "finish", "mark", "tick", "uncheck", "refine", "detail", "more steps", "more detailed", "add a step", "add steps"]
    is_mutation_request = any(word in query_lower for word in mutation_words)
    
    # Use LLM to extract target plan name / keywords if it's a mutation/refinement
    search_query = last_user_query
    if is_mutation_request:
        try:
            llm_extract = ChatOpenAI(
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
                model=LLM_MODEL,
                temperature=0
            )
            extract_prompt = (
                "You are an assistant that extracts the target plan title, keywords, or ID that the user is referring to "
                "in their latest message in the conversation history.\n"
                "Return ONLY the plain text keywords or ID (e.g., 'Build a Zoo' or 'plan_001') to search the database. "
                "If they are referring to all tasks, return 'all'. If they are not referring to any specific existing plan, "
                "just return the latest message content."
            )
            extract_messages = [SystemMessage(content=extract_prompt)]
            for msg in messages[-5:]:
                extract_messages.append(msg)
            
            res = llm_extract.invoke(extract_messages).content.strip()
            if res:
                search_query = res
        except Exception:
            pass

    # Retrieve matching plans
    if search_query.lower() == "all":
        from tools.db_tools import get_all_plans
        retrieved_plans = get_all_plans()
    else:
        retrieved_plans = query_plans(search_query, limit=5)
    
    if is_mutation_request:
        new_messages = list(messages)
        new_messages.append(AIMessage(content=f"[System Retrieved] Matching tasks from database:\n{json.dumps(retrieved_plans)}"))
        return {
            "messages": new_messages,
            "next_agent": "supervisor"
        }
        
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
