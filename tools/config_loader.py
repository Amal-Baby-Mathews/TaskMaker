import os
import json

# Define the root configuration file path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    """
    Loads config.json and returns LLM configuration settings.
    Falls back to environment variables and defaults if config.json does not exist.
    """
    config_data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config_data = json.load(f)
        except Exception as e:
            # Fallback to empty if json loading fails
            pass

    # Retrieve values with config.json prioritizing over env variables, prioritizing over default fallback
    llm_base_url = config_data.get("llm_base_url") or os.getenv("LLM_BASE_URL", "http://localhost:9999/v1")
    llm_model = config_data.get("llm_model") or os.getenv("LLM_MODEL", "openai-compatible-model")
    llm_api_key = config_data.get("llm_api_key") or os.getenv("LLM_API_KEY", "sk-no-key-required")

    return {
        "LLM_BASE_URL": llm_base_url,
        "LLM_MODEL": llm_model,
        "LLM_API_KEY": llm_api_key
    }
