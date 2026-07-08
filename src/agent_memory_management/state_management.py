from pathlib import Path
import os
import json

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

CONFIG_FILE = Path.home() / ".codeman_config.json"
CHATS_DIR = Path.home() / ".codeman_chats"
CHATS_DIR.mkdir(exist_ok=True)



def load_saved_config(console):
    if CONFIG_FILE.exists():
        try:
            data = CONFIG_FILE.read_text().strip()
            if not data: return None
            config = json.loads(data)

            # 👇 FORCE RE-INJECTION: Ensure these map perfectly to the operating system memory
            if config.get("endpoint"):
                os.environ["AZURE_OPENAI_ENDPOINT"] = config["endpoint"]
            if config.get("api_version"):
                os.environ["AZURE_OPENAI_API_VERSION"] = config["api_version"]
            if config.get("api_key"):
                os.environ["AZURE_OPENAI_API_KEY"] = config["api_key"]
            if config.get("anthropic_key"):
                os.environ["ANTHROPIC_API_KEY"] = config["anthropic_key"]
            if config.get("openai_key"):
                os.environ["OPENAI_API_KEY"] = config["openai_key"]

            return config
        except Exception as e:
            console.print(f"[yellow]⚠️ Failed to read config: {e}[/yellow]")
            return None
    return None

def save_config(model_name: str, use_entra_id: bool):
    # Dynamically bundle whatever is currently in the environment state
    config_data = {
        "model_name": model_name,
        "use_entra_id": use_entra_id,
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", ""),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai_key": os.getenv("OPENAI_API_KEY", "")
    }
    CONFIG_FILE.write_text(json.dumps(config_data, indent=2))


def save_chat_session(session_id: str, history: list[ModelMessage], console):
    chat_file = CHATS_DIR / f"{session_id}.json"
    try:
        json_str = ModelMessagesTypeAdapter.dump_json(history, indent=2).decode('utf-8')
        chat_file.write_text(json_str)
    except Exception as e:
        console.print(f"\n[yellow]⚠️ Warning: Failed to sync history matrix to disk: {e}[/yellow]")


def load_chat_session(session_id: str, console):
    chat_file = CHATS_DIR / f"{session_id}.json"
    if not chat_file.exists(): return []
    try:
        raw_data = json.loads(chat_file.read_text())
        return ModelMessagesTypeAdapter.validate_python(raw_data)
    except Exception:
        console.print("\n[yellow]⚠️ Warning: Conversation cache file was corrupted. Starting fresh.[/yellow]")
        return []