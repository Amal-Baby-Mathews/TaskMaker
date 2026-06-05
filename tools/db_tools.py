import os
import chromadb
from typing import Optional, List, Dict, Any

# Resolve database path relative to this workspace
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")

# Initialize ChromaDB client in persistent/embedded mode
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="TaskMaker_plans")

def add_plan(plan_id: str, title: str, description: str, due_time: str, status: str = "pending") -> str:
    """
    Adds a new plan to ChromaDB. If the plan_id already exists, resolves the collision
    by incrementing the numeric suffix, and returns the final plan_id used.
    """
    # Check if ID already exists
    existing = collection.get(ids=[plan_id])
    if existing and existing.get("ids") and len(existing["ids"]) > 0:
        import re
        match = re.match(r"^(.*?)(_?)(\d+)$", plan_id)
        if match:
            base, sep, num_str = match.groups()
            num = int(num_str)
            width = len(num_str)
            while True:
                num += 1
                new_id = f"{base}{sep}{num:0{width}d}"
                existing_check = collection.get(ids=[new_id])
                if not (existing_check and existing_check.get("ids") and len(existing_check["ids"]) > 0):
                    plan_id = new_id
                    break
        else:
            counter = 1
            while True:
                new_id = f"{plan_id}_{counter}"
                existing_check = collection.get(ids=[new_id])
                if not (existing_check and existing_check.get("ids") and len(existing_check["ids"]) > 0):
                    plan_id = new_id
                    break

    # Ensure none of the metadata values are None to prevent ChromaDB serialization issues
    title_str = title or ""
    desc_str = description or ""
    due_str = due_time or ""
    status_str = status or "pending"

    doc = f"Plan ID: {plan_id}\nTitle: {title_str}\nDescription: {desc_str}\nDue Time: {due_str}\nStatus: {status_str}"
    metadata = {
        "plan_id": plan_id,
        "title": title_str,
        "description": desc_str,
        "due_time": due_str,
        "status": status_str
    }
    collection.add(
        ids=[plan_id],
        documents=[doc],
        metadatas=[metadata]
    )
    return plan_id

def update_plan(
    plan_id: str, 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    due_time: Optional[str] = None, 
    status: Optional[str] = None
) -> None:
    """
    Updates an existing plan in ChromaDB.
    """
    existing = collection.get(ids=[plan_id])
    if not existing or not existing.get("metadatas") or len(existing["metadatas"]) == 0:
        raise ValueError(f"Plan with ID {plan_id} not found.")
    
    current_metadata = existing["metadatas"][0]
    
    # Merge updates and ensure safe string conversion (no None values in metadata)
    new_metadata = dict(current_metadata)
    if title is not None:
        new_metadata["title"] = title or ""
    if description is not None:
        new_metadata["description"] = description or ""
    if due_time is not None:
        new_metadata["due_time"] = due_time or ""
    if status is not None:
        new_metadata["status"] = status or "pending"
        
    doc = f"Plan ID: {plan_id}\nTitle: {new_metadata['title']}\nDescription: {new_metadata['description']}\nDue Time: {new_metadata['due_time']}\nStatus: {new_metadata['status']}"
    
    collection.update(
        ids=[plan_id],
        documents=[doc],
        metadatas=[new_metadata]
    )

def delete_plan(plan_id: str) -> List[str]:
    """
    Deletes a plan or multiple plans from ChromaDB.
    Supports:
      - Specific ID (e.g., 'plan_001')
      - 'all' to delete all plans
      - 'query:<term>' to delete plans matching a substring or search term
    Returns a list of plan IDs that were deleted.
    """
    if plan_id == "all":
        all_plans = get_all_plans()
        ids = [p["plan_id"] for p in all_plans]
        if ids:
            collection.delete(ids=ids)
        return ids

    if plan_id.startswith("query:"):
        query_term = plan_id[len("query:"):].lower()
        all_plans = get_all_plans()
        
        # 1. Substring matches (safe, case-insensitive)
        matched_ids = []
        for p in all_plans:
            title = p.get("title", "").lower()
            desc = p.get("description", "").lower()
            pid = p.get("plan_id", "").lower()
            if query_term in title or query_term in desc or query_term in pid:
                matched_ids.append(p["plan_id"])
                
        # 2. Semantic query fallback if no substring match found
        if not matched_ids and collection.count() > 0:
            results = query_plans(query_term, limit=10)
            matched_ids = [p["plan_id"] for p in results]
            
        if matched_ids:
            collection.delete(ids=matched_ids)
            return matched_ids
        else:
            raise ValueError(f"No reminders matching '{query_term}' found.")

    # Normal single ID deletion
    existing = collection.get(ids=[plan_id])
    if not existing or not existing.get("metadatas") or len(existing["metadatas"]) == 0:
        raise ValueError(f"Plan with ID {plan_id} not found.")
    collection.delete(ids=[plan_id])
    return [plan_id]

def create_repeating_plan(
    plan_id: str,
    title: str,
    description: str,
    start_time: str,
    frequency: str,      # "daily" or "weekly"
    count: int,          # Number of occurrences
    status: str = "pending"
) -> List[str]:
    """
    Creates multiple occurrences of a repeating plan in ChromaDB.
    Returns a list of all successfully created plan IDs.
    """
    from datetime import datetime, timedelta
    
    start_dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            start_dt = datetime.strptime(start_time, fmt)
            break
        except ValueError:
            continue
            
    if not start_dt:
        try:
            # Handle standard ISO timestamp formats
            start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
        except ValueError:
            raise ValueError(f"Invalid start_time format: {start_time}. Expected YYYY-MM-DDTHH:MM:SS")
            
    created_ids = []
    delta = timedelta(days=1) if frequency == "daily" else timedelta(weeks=1)
    
    for i in range(count):
        current_dt = start_dt + (i * delta)
        current_time_str = current_dt.isoformat()
        
        # Clean numeric suffix generation
        instance_id = f"{plan_id}_{i+1}"
        
        actual_id = add_plan(
            plan_id=instance_id,
            title=f"{title} (Occurrence {i+1})",
            description=description,
            due_time=current_time_str,
            status=status
        )
        created_ids.append(actual_id)
        
    return created_ids

def query_plans(query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Queries plans in ChromaDB using vector similarity search.
    """
    # If the collection is empty, querying might return empty results
    if collection.count() == 0:
        return []
        
    results = collection.query(
        query_texts=[query_text],
        n_results=limit
    )
    
    plans = []
    if results and results.get("metadatas") and len(results["metadatas"]) > 0:
        for metadata in results["metadatas"][0]:
            if metadata:
                plans.append(metadata)
    return plans

def get_all_plans() -> List[Dict[str, Any]]:
    """
    Retrieves all plans stored in ChromaDB.
    """
    results = collection.get()
    plans = []
    if results and results.get("metadatas"):
        for metadata in results["metadatas"]:
            if metadata:
                plans.append(metadata)
    return plans

# Dedicated rules collection and rules CRUD helpers
rules_collection = client.get_or_create_collection(name="system_rules")

def add_rule(rule_id: str, content: str) -> str:
    """
    Adds a new rule to ChromaDB. If rule_id collision occurs, resolves collision
    by incrementing the numeric suffix, and returns the final rule_id used.
    """
    existing = rules_collection.get(ids=[rule_id])
    if existing and existing.get("ids") and len(existing["ids"]) > 0:
        import re
        match = re.match(r"^(.*?)(_?)(\d+)$", rule_id)
        if match:
            base, sep, num_str = match.groups()
            num = int(num_str)
            width = len(num_str)
            while True:
                num += 1
                new_id = f"{base}{sep}{num:0{width}d}"
                existing_check = rules_collection.get(ids=[new_id])
                if not (existing_check and existing_check.get("ids") and len(existing_check["ids"]) > 0):
                    rule_id = new_id
                    break
        else:
            counter = 1
            while True:
                new_id = f"{rule_id}_{counter}"
                existing_check = rules_collection.get(ids=[new_id])
                if not (existing_check and existing_check.get("ids") and len(existing_check["ids"]) > 0):
                    rule_id = new_id
                    break

    content_str = content or ""
    metadata = {
        "rule_id": rule_id,
        "content": content_str
    }
    rules_collection.add(
        ids=[rule_id],
        documents=[content_str],
        metadatas=[metadata]
    )
    return rule_id

def delete_rule(rule_id: str) -> List[str]:
    """
    Deletes a rule or all rules from ChromaDB.
    """
    if rule_id == "all":
        all_rules = get_all_rules()
        ids = [r["rule_id"] for r in all_rules]
        if ids:
            rules_collection.delete(ids=ids)
        return ids

    existing = rules_collection.get(ids=[rule_id])
    if not existing or not existing.get("metadatas") or len(existing["metadatas"]) == 0:
        raise ValueError(f"Rule with ID {rule_id} not found.")
    rules_collection.delete(ids=[rule_id])
    return [rule_id]

def get_all_rules() -> List[Dict[str, Any]]:
    """
    Retrieves all rules stored in ChromaDB.
    """
    results = rules_collection.get()
    rules = []
    if results and results.get("metadatas"):
        for metadata in results["metadatas"]:
            if metadata:
                rules.append(metadata)
    return rules

def query_rules(query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Queries rules in ChromaDB using vector similarity search.
    """
    if rules_collection.count() == 0:
        return []
        
    results = rules_collection.query(
        query_texts=[query_text],
        n_results=limit
    )
    
    rules = []
    if results and results.get("metadatas") and len(results["metadatas"]) > 0:
        for metadata in results["metadatas"][0]:
            if metadata:
                rules.append(metadata)
    return rules

# Chat history collection and CRUD helpers
chat_history_collection = client.get_or_create_collection(name="chat_history")

def save_chat_history(messages: List[Any]) -> None:
    """
    Serializes and persists the chat history in ChromaDB.
    """
    import json
    serialized = []
    for msg in messages:
        msg_type = "human"
        if msg.type == "ai":
            msg_type = "ai"
        elif msg.type == "system":
            msg_type = "system"
            
        serialized.append({
            "type": msg_type,
            "content": msg.content
        })
    
    content_str = json.dumps(serialized)
    metadata = {
        "chat_id": "last_chat",
        "content": content_str
    }
    chat_history_collection.upsert(
        ids=["last_chat"],
        documents=[content_str],
        metadatas=[metadata]
    )

def load_chat_history() -> List[Any]:
    """
    Retrieves and deserializes the last saved chat history from ChromaDB.
    """
    import json
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    results = chat_history_collection.get(ids=["last_chat"])
    if not results or not results.get("metadatas") or len(results["metadatas"]) == 0:
        return []
    
    metadata = results["metadatas"][0]
    if not metadata or "content" not in metadata:
        return []
        
    try:
        data = json.loads(metadata["content"])
        messages = []
        for item in data:
            t = item.get("type")
            content = item.get("content", "")
            if t == "human":
                messages.append(HumanMessage(content=content))
            elif t == "ai":
                messages.append(AIMessage(content=content))
            elif t == "system":
                messages.append(SystemMessage(content=content))
        return messages
    except Exception:
        return []

def clear_chat_history() -> None:
    """
    Deletes the saved chat history from ChromaDB.
    """
    existing = chat_history_collection.get(ids=["last_chat"])
    if existing and existing.get("ids") and len(existing["ids"]) > 0:
        chat_history_collection.delete(ids=["last_chat"])
