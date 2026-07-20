import os
import sys
import getpass
from rich.panel import Panel
from rich.console import Group
from pydantic_ai.messages import ModelRequest, ModelResponse,UserPromptPart, TextPart, ToolCallPart
from rich.markdown import Markdown
import json

def get_graceful_input(console, prompt_msg: str, is_secret: bool = False) -> str:
    """A single unified input handler that supports graceful exits and optional masking for secrets."""
    console.print(prompt_msg, end="")

    # Dynamically toggle between hidden getpass and standard visible input
    user_input = getpass.getpass("").strip() if is_secret else input("").strip()

    if user_input.lower() in ["exit", "quit"]:
        console.print("[yellow]👋 Configuration aborted. Safely exiting CodeMan.[/yellow]")
        sys.exit(0)

    return user_input

def force_menu_config(force_menu, target_model, use_entra_id):
    if not force_menu:
        is_azure = target_model.startswith("azure:")
        is_anthropic = target_model.startswith("anthropic:")
        is_openai = target_model.startswith("openai:")

        missing_azure = is_azure and (not os.getenv("AZURE_OPENAI_ENDPOINT") or (
                not use_entra_id and not os.getenv("AZURE_OPENAI_API_KEY")))
        missing_anthropic = is_anthropic and not os.getenv("ANTHROPIC_API_KEY")
        missing_openai = is_openai and not os.getenv("OPENAI_API_KEY")

        if missing_azure or missing_anthropic or missing_openai:
            # Force the setup menu to open so user can input their correct key strings
            force_menu = True

    return force_menu


def show_menu_options(console):
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("========================================================", style="bold blue")
    console.print("         🤖 CODEMAN SECURITY INTERFACE: MODULE SETUP     ", style="bold white")
    console.print("========================================================", style="bold blue")
    console.print("Select your underlying model provider and authentication:")
    console.print("  [[bold cyan]1[/bold cyan]] Azure OpenAI -> Microsoft Entra ID (Passwordless)")
    console.print("  [[bold cyan]2[/bold cyan]] Azure OpenAI -> Static Secret API Key Approach")
    console.print("  [[bold cyan]3[/bold cyan]] Anthropic Claude   (Requires ANTHROPIC_API_KEY)")
    console.print("  [[bold cyan]4[/bold cyan]] OpenAI GPT-4o      (Requires OPENAI_API_KEY)")
    console.print("  [[bold cyan]5[/bold cyan]] Local Ollama       (Air-Gapped / No Keys Needed)")
    console.print("========================================================", style="bold blue")


def choose_options(console):
    choice = input("Enter choice (1-5):  ").strip()
    if choice == '1':
        use_entra_id = True
        console.print("\n[bold cyan]🔧 Configuring Azure OpenAI (Entra ID Passwordless)[/bold cyan]")

        env_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "").strip()
        if not env_model:
            env_model = get_graceful_input(prompt_msg="Enter your Azure Deployment / Model Name: (type exit if you want to exit) ", console=console)
            if not env_model: raise ValueError("Azure Deployment Name cannot be empty.")
        target_model = f"azure:{env_model}" if not env_model.startswith("azure:") else env_model

        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            endpoint = get_graceful_input(prompt_msg=
                "Enter your Azure Endpoint URL (e.g., https://your-res.openai.azure.com/):  (type exit if you want to exit)", console=console)
            if not endpoint: raise ValueError("Azure Endpoint URL cannot be empty.")
            os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint

        if not os.getenv("AZURE_OPENAI_API_VERSION"):
            api_ver = get_graceful_input(prompt_msg=
                "Enter Azure API Version [Default: 2025-04-01-preview]: (type exit if you want to exit) ", console=console)
            os.environ["AZURE_OPENAI_API_VERSION"] = api_ver if api_ver else "2025-04-01-preview"
        return target_model, use_entra_id

    elif choice == '2':
        use_entra_id = False
        console.print("\n[bold cyan]🔧 Configuring Azure OpenAI (Static Secret API Key)[/bold cyan]")

        env_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "").strip()
        if not env_model:
            env_model = get_graceful_input(prompt_msg="Enter your Azure Deployment / Model Name:  (type exit if you want to exit)", console=console)
            if not env_model: raise ValueError("Azure Deployment Name cannot be empty.")
        target_model = f"azure:{env_model}" if not env_model.startswith("azure:") else env_model

        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            endpoint = get_graceful_input(prompt_msg=
                "Enter your Azure Endpoint URL (e.g., https://your-res.openai.azure.com/): (type exit if you want to exit) ", console=console)
            if not endpoint: raise ValueError("Azure Endpoint URL cannot be empty.")
            os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint

        if not os.getenv("AZURE_OPENAI_API_VERSION"):
            api_ver = get_graceful_input(prompt_msg=
                "Enter Azure API Version [Default: 2025-04-01-preview]: (type exit if you want to exit) ", console=console)
            os.environ["AZURE_OPENAI_API_VERSION"] = api_ver if api_ver else "2025-04-01-preview"

        if not os.getenv("AZURE_OPENAI_API_KEY"):
            # console.print("\n🔒 [yellow][SECURITY INTERCEPT] AZURE_OPENAI_API_KEY is missing.[/yellow]")
            user_key = get_graceful_input(prompt_msg=
                "🔒 [yellow]AZURE_OPENAI_API_KEY is missing.[/yellow] Enter Key: (type exit if you want to exit) ",
                is_secret=True, console=console)
            if not user_key: raise ValueError("Azure API Key cannot be empty.")
            os.environ["AZURE_OPENAI_API_KEY"] = user_key
        return target_model, use_entra_id
    elif choice == '3':
        console.print("\n[grey50]Default: anthropic:claude-3-5-sonnet[/grey50]")
        custom_model = get_graceful_input(prompt_msg="Enter Anthropic model name (type exit if you want to exit): ", console=console)
        target_model = custom_model if custom_model else "anthropic:claude-3-5-sonnet"
        use_entra_id = False

        if not os.getenv("ANTHROPIC_API_KEY"):
            # console.print("\n🔒 [yellow][SECURITY INTERCEPT] ANTHROPIC_API_KEY is missing.[/yellow]")
            user_key = get_graceful_input(prompt_msg=
                "\n🔒 [yellow][SECURITY INTERCEPT] ANTHROPIC_API_KEY is missing.[/yellow]\nEnter Key:  (type exit if you want to exit)",
                is_secret=True, console=console)
            if not user_key: raise ValueError("Anthropic API Key cannot be empty.")
            os.environ["ANTHROPIC_API_KEY"] = user_key
        return target_model, use_entra_id
    elif choice == '4':
        console.print("\n[grey50]Default: openai:gpt-4o[/grey50]")
        custom_model = get_graceful_input(prompt_msg=
            "Enter OpenAI model name (or press Enter for default): (type exit if you want to exit) ", console=console)
        target_model = custom_model if custom_model else "openai:gpt-4o"
        use_entra_id = False

        if not os.getenv("OPENAI_API_KEY"):
            # console.print("\n🔒 [yellow][SECURITY INTERCEPT] OPENAI_API_KEY is missing.[/yellow]")
            user_key = get_graceful_input(prompt_msg=
                "\n🔒 [yellow][SECURITY INTERCEPT] OPENAI_API_KEY is missing.[/yellow]\nEnter Key: (type exit if you want to exit) ",
                is_secret=True, console=console)
            if not user_key: raise ValueError("OpenAI API Key cannot be empty.")
            os.environ["OPENAI_API_KEY"] = user_key
        return target_model, use_entra_id
    elif choice == '5':
        console.print("\n[grey50]Default: ollama:llama3[/grey50]")
        custom_model = get_graceful_input( prompt_msg=
            "Enter Ollama model name (or press Enter for default): (type exit if you want to exit) ", console=console)
        target_model = custom_model if custom_model else "ollama:llama3"
        use_entra_id = False

        return target_model, use_entra_id

    else:
        console.print("[red]❌ Invalid choice. Exiting.[/red]")
        return  None, None



def session_options(console):
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("========================================================", style="bold blue")
    console.print("         💬 CODEMAN SESSION CHASSIS MANAGEMENT           ", style="bold white")
    console.print("========================================================", style="bold blue")
    console.print("  [[bold cyan]1[/bold cyan]] Start a completely fresh conversation workspace")
    console.print("  [[bold cyan]2[/bold cyan]] Resume your last cached memory session")
    console.print("========================================================", style="bold blue")
    session_choice = input("Enter choice (1-2): ").strip()
    return session_choice


def print_harness_screen(console, model_name, auth_method, history_count: int):
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("\n")
    console.print("      ██████╗ ██████╗ ██████╗ ███████╗███╗   ███╗ █████╗ ███╗   ██╗", style="bold cyan")
    console.print("      ██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║", style="bold cyan")
    console.print("      ██║     ██║   ██║██║  ██║█████╗  ██╔████╔██║███████║██╔██╗ ██║", style="bold cyan")
    console.print("      ██║     ██║   ██║██║  ██║██╔══╝  ██║╚██╔╝██║██╔══██║██║╚██╗██║", style="bold cyan")
    console.print("      ╚██████╗╚██████╔╝██████╔╝███████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║", style="bold cyan")
    console.print("       ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝", style="bold cyan")
    console.print("\n")
    console.print(
        f"      [grey50]Engine:[/grey50] [bold]{model_name}[/bold]  ·  [grey50]Auth:[/grey50] [green]{auth_method}[/green]  ·  [grey50]Context nodes:[/grey50] [cyan]{history_count}[/cyan]")
    # 👇 UPDATED: Clear navigation commands explicitly documented for the user
    console.print(
        f"      [grey50][Type CTRL+D to [bold white]submit[/bold white] query . Type [bold white]menu[/bold white] or [bold white]swap[/bold white] to change profiles  ·  Type [bold white]exit[/bold white] or [bold white]quit[/bold white] to safely close CodeMan][/grey50]\n")


def llm_ui_panels(console):
    console.print("[grey50]🔄 Initializing live streaming token layers...[/grey50]")

    panel_reasoning = Panel("", title="🧠 [bold orange3]AI Live Reasoning Chain[/bold orange3]",
                            border_style="orange3")
    panel_answer = Panel("", title="🎯 [bold green]Live Generated Response[/bold green]", border_style="green")
    ui_group = Group(panel_reasoning, panel_answer)

    return panel_reasoning, panel_answer, ui_group


def display_chat_history(chat_history, console):

    for message in chat_history:
        # 1. Capture Past User Prompts
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    console.print(f"\n[bold green]👤 You:[/bold green] {part.content}")


        # 2. Capture Past AI Structured Text Responses
        elif isinstance(message, ModelResponse):

            for part in message.parts:

                if isinstance(part, ToolCallPart):

                    if part.tool_name == "final_result":
                        try:
                            ai_output= json.loads(part.args) if isinstance(part.args, str) else part.args
                            answer = ai_output.get("answer", "")

                            if answer:
                                console.print(f"\n[bold cyan]🤖 CodeMan:[/bold cyan]")
                                console.print(Markdown(answer))


                        except Exception:
                            pass  # Fallback to printing raw text if parsing hits validation noise
                            # Standalone flat string fallback (if it's ever used)
                    elif isinstance(part, TextPart) and part.content.strip():
                        # Double-check it isn't raw schema JSON layout strings
                        if not (part.content.strip().startswith("{") and part.content.strip().endswith("}")):
                            console.print(f"\n[bold cyan]🤖 CodeMan:[/bold cyan]")
                            console.print(Markdown(part.content.strip()))

    console.print("\n" + "─" * 70 + "\n")






def show_menu(force_menu, target_model, use_entra_id, console):
    force_menu = force_menu_config(force_menu, target_model, use_entra_id)
    if force_menu:
        show_menu_options(console)
        new_target_model, new_use_entra_id = choose_options(console)
        if new_target_model is not None and new_use_entra_id is not  None:
            target_model = new_target_model
            use_entra_id = new_use_entra_id
    return target_model, use_entra_id
