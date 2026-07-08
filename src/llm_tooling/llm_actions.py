# llm_actions.py
import os
from pathlib import Path
from src.llm_tooling.sandbox import DockerSandbox

try:
    sandbox_engine = DockerSandbox()
except Exception as docker_err:
    print(f"\033[93m⚠️ Warning: Sandboxing framework offline. Falling back to local host: {docker_err}\033[0m")
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
            summary += readme_path.read_text(encoding='utf-8')[:1000] + "...\n"
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
        return path.read_text(encoding='utf-8')
    except Exception as e:
        return f"❌ Error reading file: {e}"


def write_repo_file(file_path: str, content: str) -> str:
    """Creates or overwrites a file in the repository with new code or content.

    Args:
        file_path: The relative path to the target file.
        content: The complete, exact text content to write into the file.
    """
    print(f"\n\033[93m🔔 AI wants to write to '{file_path}'. Allow? (y/n):\033[0m ", end="", flush=True)

    # Read a single character cleanly depending on OS to bypass buffering locks
    if os.name == 'nt':
        import msvcrt
        confirm = msvcrt.getch().decode('utf-8').lower()
        print(confirm)  # Echo choice
    else:
        import sys
        # Read directly from standard input stream without waiting for a newline buffer
        confirm = sys.stdin.read(1).lower()
        if confirm not in ['\n', '\r']:
            print(confirm)  # Echo choice

    if confirm != 'y':
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
    """
    Executes a lint, syntax check, or test command INSIDE A SECURE ISOLATED SANDBOX.
    Use this immediately after writing or modifying files to test code safely.

    Args:
        command: The terminal execution instruction string (e.g., 'python -m py_compile script.py').
    """
    if not sandbox_engine:
        return "❌ Sandbox compilation offline. Docker Desktop engine must be running and active."

    # Execute the validation entirely inside the container workspace instance
    result = sandbox_engine.run_command_in_sandbox(command)

    if result["exit_code"] == 0:
        return f"✅ Sandbox validation successful! Environment Output:\n{result['output'] or 'No errors detected.'}"
    else:
        return (
            f"❌ CRITICAL SYNTAX OR COMPILATION ERROR DETECTED INSIDE SANDBOX:\n"
            f"Exit Status Code: {result['exit_code']}\n"
            f"Container Diagnostics Output:\n{result['output']}\n"
            f"Instructions: Adjust your code modifications to fix this specific crash, rewrite the file, and verify again."
        )