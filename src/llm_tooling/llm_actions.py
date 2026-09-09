# llm_actions.py
import os
from pathlib import Path

from rich.prompt import Confirm

from src.llm_tooling.sandbox import ContainerSandbox

try:
    sandbox_engine = ContainerSandbox()
except Exception as runtime_err:
    print(
        "\033[93m⚠️ Warning: Sandboxing framework offline: "
        f"{runtime_err}\033[0m"
    )
    sandbox_engine = None


def inspect_repository_structure(directory_path: str = ".") -> str:
    """Scans the specified directory to list folders, files, and previews README.md.

    Args:
        directory_path: The folder path to inspect (defaults to current directory).
    """
    base_path = Path(directory_path)
    if not base_path.exists():
        return f"❌ Error: The directory '{directory_path}' does not exist."

    try:
        items = list(base_path.iterdir())
        files = [item.name for item in items if item.is_file()]
        folders = [item.name for item in items if item.is_dir()]

        summary = f"📁 Folders found: {', '.join(folders) if folders else 'None'}\n"
        summary += f"📄 Files found: {', '.join(files) if files else 'None'}\n\n"

        readme_path = base_path / "README.md"
        if readme_path.exists():
            summary += "📖 Found a README.md! Here is a preview:\n"
            summary += readme_path.read_text(encoding="utf-8")[:1000] + "...\n"
        else:
            summary += "⚠️ No README.md found to explain the project purpose.\n"

        return summary
    except Exception as e:
        return f"❌ Error scanning directory: {e}"


def read_repo_file(file_path: str) -> str:
    """Reads the contents of a specific file in the repository so it can be inspected.

    Args:
        file_path: The relative path to the file from the workspace root.
    """
    path = Path(file_path)
    if not path.exists():
        return f"❌ Error: File '{file_path}' does not exist."
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Error reading file: {e}"


def write_repo_file(file_path: str, content: str, console=None) -> str:
    """Creates or overwrites a file in the repository with new code or content.

    Args:
        file_path: The relative path to the target file.
        content: The complete, exact text content to write into the file.
        console: Optional Rich Console instance.
    """
    if console is not None:
        console.print(
            f"\n[bold yellow]🔔 AI wants to write to [cyan]'{file_path}'[/cyan].[/bold yellow]"
        )
        if not Confirm.ask("Allow modification?", default=False, console=console):
            return "❌ Action rejected by the user. Do not modify the file."
    else:
        print(
            f"\n\033[93m🔔 AI wants to write to '{file_path}'. Allow? (y/n):\033[0m ",
            end="",
            flush=True,
        )
        if os.name == "nt":
            import msvcrt

            confirm = msvcrt.getch().decode("utf-8").lower()
            print(confirm)
        else:
            import sys

            confirm = sys.stdin.read(1).lower()
            if confirm not in ["\n", "\r"]:
                print(confirm)
        if confirm != "y":
            return "❌ Action rejected by the user. Do not modify the file."

    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return f"✅ Successfully wrote and updated '{file_path}'."
    except Exception as e:
        return f"❌ Error writing to file '{file_path}': {e}"


def verify_code_health(command: str = "python -m py_compile *.py") -> str:
    """Execute a check inside an isolated Podman or Docker container.

    Args:
        command: Terminal instruction such as ``python -m pytest``.
    """
    if not sandbox_engine:
        return (
            "❌ Sandbox offline. Start Podman with `podman machine start` "
            "(macOS/Windows), or `systemctl --user start podman.socket` "
            "(Linux), then restart CodeMan. Docker is not required."
        )

    result = sandbox_engine.run_command_in_sandbox(command)
    runtime = sandbox_engine.runtime
    if result["exit_code"] == 0:
        return (
            f"✅ {runtime} sandbox validation successful! Environment Output:\n"
            f"{result['output'] or 'No errors detected.'}"
        )
    return (
        f"❌ CRITICAL ERROR DETECTED INSIDE {runtime.upper()} SANDBOX:\n"
        f"Exit Status Code: {result['exit_code']}\n"
        f"Container Diagnostics Output:\n{result['output']}\n"
        "Instructions: Adjust your code modifications to fix this specific crash, "
        "rewrite the file, and verify again."
    )
