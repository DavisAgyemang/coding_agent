from datetime import datetime
from pathlib import Path
import json
import os
import re

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

CONFIG_FILE = Path.home() / ".codeman_config.json"
CHATS_DIR = Path.home() / ".codeman_chats"
CHATS_DIR.mkdir(exist_ok=True)


def load_saved_config(console):
    if CONFIG_FILE.exists():
        try:
            data = CONFIG_FILE.read_text().strip()
            if not data:
                return None
            config = json.loads(data)

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
    config_data = {
        "model_name": model_name,
        "use_entra_id": use_entra_id,
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", ""),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai_key": os.getenv("OPENAI_API_KEY", ""),
    }
    CONFIG_FILE.write_text(json.dumps(config_data, indent=2))


def _chat_file(session_id: str) -> Path:
    """Return a safe chat path and reject path traversal/session name abuse."""
    if not session_id or not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        raise ValueError("Invalid chat session ID.")
    return CHATS_DIR / f"{session_id}.json"


def create_chat_session_id(name: str = "") -> str:
    """Create a readable, unique ID suitable for use as a chat filename."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip()).strip("-").lower()
    slug = slug[:40] or "chat"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{slug}-{timestamp}"


def list_chat_sessions() -> list[dict]:
    """List saved chats newest first with stable IDs and display details."""
    sessions = []
    if not CHATS_DIR.exists():
        return sessions

    for chat_file in CHATS_DIR.glob("*.json"):
        try:
            stat = chat_file.stat()
            raw_data = json.loads(chat_file.read_text())
            message_count = len(raw_data) if isinstance(raw_data, list) else 0
            sessions.append(
                {
                    "session_id": chat_file.stem,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "message_count": message_count,
                }
            )
        except (OSError, ValueError, json.JSONDecodeError):
            # Keep corrupted sessions visible so users can remove them.
            try:
                sessions.append(
                    {
                        "session_id": chat_file.stem,
                        "modified": datetime.fromtimestamp(chat_file.stat().st_mtime),
                        "message_count": 0,
                    }
                )
            except OSError:
                continue

    return sorted(sessions, key=lambda session: session["modified"], reverse=True)


def delete_chat_session(session_id: str, console=None) -> bool:
    """Delete one saved chat. Confirmation is handled by the session picker."""
    try:
        chat_file = _chat_file(session_id)
        if not chat_file.exists():
            return False
        chat_file.unlink()
        return True
    except (OSError, ValueError) as exc:
        if console is not None:
            console.print(f"[red]❌ Could not delete chat history: {exc}[/red]")
        return False


def _print_saved_chats(console, sessions, current_session_id=None):
    if not sessions:
        console.print("[yellow]No saved chat histories were found.[/yellow]")
        return
    console.print("\n[bold]Saved chat histories (newest first):[/bold]")
    for index, session in enumerate(sessions, start=1):
        modified = session["modified"].strftime("%Y-%m-%d %H:%M")
        current = " [bold green]← current[/bold green]" if session["session_id"] == current_session_id else ""
        console.print(
            f"  [[bold cyan]{index}[/bold cyan]] {session['session_id']} "
            f"[grey50]({session['message_count']} messages, {modified})[/grey50]{current}"
        )


def switch_chat_session(
    current_session_id: str,
    current_history: list[ModelMessage],
    console,
) -> tuple[str, list[ModelMessage]]:
    """Select another saved chat from inside the active conversation window."""
    # Persist the active chat before presenting the switcher so no completed turn is lost.
    save_chat_session(current_session_id, current_history, console)
    sessions = list_chat_sessions()
    _print_saved_chats(console, sessions, current_session_id=current_session_id)

    if len(sessions) < 2:
        console.print("[yellow]There are no other saved chat histories to switch to.[/yellow]")
        input("Press Enter to return to the current chat...")
        return current_session_id, current_history

    while True:
        raw_index = input(
            "Enter the number of the chat to switch to (or b to cancel): "
        ).strip()
        if raw_index.lower() == "b":
            console.print("[cyan]Chat switch cancelled.[/cyan]")
            return current_session_id, current_history

        try:
            selected_index = int(raw_index) - 1
            if selected_index < 0:
                raise IndexError
            selected_session_id = sessions[selected_index]["session_id"]
        except (ValueError, IndexError):
            console.print("[red]That chat history number is invalid.[/red]")
            continue

        if selected_session_id == current_session_id:
            console.print("[yellow]That chat is already active. Choose another number or b.[/yellow]")
            continue

        history = load_chat_session(selected_session_id, console)
        console.print(f"[green]✓ Switched to chat history: {selected_session_id}[/green]")
        return selected_session_id, history


def choose_chat_session(console) -> tuple[str, list[ModelMessage]]:
    """Interactively create, resume, or safely delete named chat histories."""
    while True:
        console.print("\n========================================================", style="bold blue")
        console.print("         💬 CODEMAN CHAT HISTORY MANAGEMENT              ", style="bold white")
        console.print("========================================================", style="bold blue")
        console.print("  [[bold cyan]1[/bold cyan]] Start and save a new chat history")
        console.print("  [[bold cyan]2[/bold cyan]] Continue a saved chat history")
        console.print("  [[bold cyan]3[/bold cyan]] Delete a saved chat history")
        console.print("========================================================", style="bold blue")
        choice = input("Enter choice (1-3): ").strip()

        if choice == "1":
            name = input("Give this chat a name (optional): ").strip()
            session_id = create_chat_session_id(name)
            save_chat_session(session_id, [], console)
            console.print(f"[green]✓ Created chat history: {session_id}[/green]")
            return session_id, []

        if choice not in {"2", "3"}:
            console.print("[red]Please enter 1, 2, or 3.[/red]")
            continue

        sessions = list_chat_sessions()
        _print_saved_chats(console, sessions)
        if not sessions:
            continue

        action = "continue" if choice == "2" else "delete"
        raw_index = input(f"Enter the number of the chat to {action} (or b to go back): ").strip()
        if raw_index.lower() == "b":
            continue
        try:
            selected_index = int(raw_index) - 1
            if selected_index < 0:
                raise IndexError
            selected = sessions[selected_index]
        except (ValueError, IndexError):
            console.print("[red]That chat history number is invalid.[/red]")
            continue

        session_id = selected["session_id"]
        if choice == "2":
            return session_id, load_chat_session(session_id, console)

        while True:
            confirmation = input(
                f"Are you sure you want to delete '{session_id}'? Type y for yes or n for no: "
            ).strip().lower()
            if confirmation in {"y", "n"}:
                break
            console.print("[yellow]Please type only y or n.[/yellow]")

        if confirmation == "n":
            console.print("[cyan]Deletion cancelled.[/cyan]")
            continue
        if delete_chat_session(session_id, console):
            console.print(f"[green]✓ Deleted chat history: {session_id}[/green]")
        else:
            console.print("[red]The selected chat history could not be deleted.[/red]")


def save_chat_session(session_id: str, history: list[ModelMessage], console):
    try:
        chat_file = _chat_file(session_id)
        json_str = ModelMessagesTypeAdapter.dump_json(history, indent=2).decode("utf-8")
        chat_file.write_text(json_str)
    except Exception as e:
        console.print(f"\n[yellow]⚠️ Warning: Failed to sync history matrix to disk: {e}[/yellow]")


def load_chat_session(session_id: str, console):
    try:
        chat_file = _chat_file(session_id)
    except ValueError as exc:
        console.print(f"\n[yellow]⚠️ Warning: {exc} Starting fresh.[/yellow]")
        return []

    if not chat_file.exists():
        return []
    try:
        raw_data = json.loads(chat_file.read_text())
        return ModelMessagesTypeAdapter.validate_python(raw_data)
    except Exception:
        console.print("\n[yellow]⚠️ Warning: Conversation cache file was corrupted. Starting fresh.[/yellow]")
        return []
