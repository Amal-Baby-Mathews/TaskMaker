import os
import datetime
import json
import inspect
import functools
from typing import Any, Dict, List

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.log")

_log_reset_done = False

def reset_log():
    """
    Truncates/resets the log file. Called on server startup.
    """
    global _log_reset_done
    if _log_reset_done:
        return
    try:
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"=== TaskMaker AI Server Log Started at {datetime.datetime.now().isoformat()} ===\n\n")
        _log_reset_done = True
    except Exception as e:
        print(f"Failed to reset log file: {e}")

def _write_log(category: str, event_name: str, details: str):
    """
    Appends a formatted log entry to server.log.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    divider = "=" * 80
    sub_divider = "-" * 80
    log_entry = (
        f"{divider}\n"
        f"[{timestamp}] [{category}] {event_name}\n"
        f"{sub_divider}\n"
        f"{details.strip()}\n"
        f"{divider}\n\n"
    )
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def log_node_start(node_name: str, state: Dict[str, Any]):
    """
    Logs the start of a LangGraph node execution, showing the input state.
    """
    serializable_state = {}
    for k, v in state.items():
        if k == "messages":
            serializable_state[k] = [
                {"role": getattr(msg, "type", type(msg).__name__), "content": getattr(msg, "content", str(msg))}
                for msg in v
            ]
        else:
            serializable_state[k] = v
            
    details = f"Input State:\n{json.dumps(serializable_state, indent=2)}"
    _write_log("NODE_EXECUTION", f"Node '{node_name}' STARTED", details)

def log_node_end(node_name: str, output: Dict[str, Any]):
    """
    Logs the completion of a LangGraph node, showing the returned updates.
    """
    details = f"Node Output / State Updates:\n{json.dumps(output, indent=2, default=str)}"
    _write_log("NODE_EXECUTION", f"Node '{node_name}' COMPLETED", details)

def log_llm_call(agent_name: str, prompt_messages: List[Any], response_content: str):
    """
    Logs an LLM model call, including the prompt inputs and the generated text.
    """
    formatted_prompts = []
    for msg in prompt_messages:
        role = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", str(msg))
        formatted_prompts.append(f"[{role.upper()}] {content}")
        
    prompt_str = "\n".join(formatted_prompts)
    details = (
        f"Prompt Messages:\n"
        f"{prompt_str}\n"
        f"\n"
        f"Model Output Response:\n"
        f"{response_content}"
    )
    _write_log("LLM_CALL", f"Agent '{agent_name}' called LLM", details)

def log_tool_call(tool_name: str, arguments: Dict[str, Any], result: Any):
    """
    Logs a database or system tool invocation.
    """
    details = (
        f"Arguments:\n"
        f"{json.dumps(arguments, indent=2, default=str)}\n"
        f"\n"
        f"Result:\n"
        f"{str(result)}"
    )
    _write_log("TOOL_CALL", f"Tool '{tool_name}' executed", details)

def log_tool(func):
    """
    Decorator to log database tool invocations.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        arguments = dict(bound.arguments)
        
        try:
            result = func(*args, **kwargs)
            log_tool_call(func.__name__, arguments, result)
            return result
        except Exception as e:
            log_tool_call(func.__name__, arguments, f"Error: {e}")
            raise
    return wrapper

# ---------------------------------------------------------------------------
# Monkeypatch BaseChatModel.invoke to catch all agent LLM calls automatically
# ---------------------------------------------------------------------------
try:
    from langchain_core.language_models.chat_models import BaseChatModel
    
    original_invoke = BaseChatModel.invoke
    
    def patched_invoke(self, input, *args, **kwargs):
        response = original_invoke(self, input, *args, **kwargs)
        try:
            agent_name = getattr(self, "model_name", "ChatOpenAI")
            # Extract content from response (could be AIMessage or string)
            content = getattr(response, "content", str(response))
            # Find the calling node or class if available
            stack = inspect.stack()
            caller_module = ""
            for frame in stack:
                module_name = frame.frame.f_globals.get("__name__", "")
                if "agents." in module_name:
                    caller_module = module_name
                    break
            display_name = f"{caller_module} ({agent_name})" if caller_module else agent_name
            log_llm_call(display_name, input, content)
        except Exception as log_err:
            print(f"Logging LLM call failed: {log_err}")
        return response

    BaseChatModel.invoke = patched_invoke
except Exception as patch_err:
    print(f"Failed to patch BaseChatModel: {patch_err}")
