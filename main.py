from src.agent_memory_management.state_management import (
    choose_chat_session,
    load_saved_config,
    save_config,
    save_chat_session,
)
from src.cli_ui.ui_config import (
    display_chat_history,
    llm_ui_panels,
    print_harness_screen,
    show_help,
    show_menu,
)
import asyncio
import os
import sys

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from src.general_tools.sanitise_chat import sanitize_history
from src.general_tools.tooling import get_custom_prompt_input
from src.llm_harness.harness import LLMHarness

# =====================================================================
#  ENVIRONMENT ENFORCEMENT LAYER
# =====================================================================
if not os.environ.get("PYTHONUNBUFFERED"):
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)

console = Console()
MAX_HISTORY_TURNS = 12  # Keeps context focused while preventing token bloat


async def main():
    config = load_saved_config(console)
    force_menu = config is None
    show_interactive_loop = True

    target_model = config["model_name"] if not force_menu else None
    use_entra_id = config["use_entra_id"] if not force_menu else True

    # 1. Select model and authentication options.
    target_model, use_entra_id = show_menu(
        force_menu, target_model, use_entra_id, console
    )
    save_config(target_model, use_entra_id)
    force_menu = False

    # 2. Select a named saved history, or create a new one.
    session_id, current_chat_history = choose_chat_session(console)

    # 3. Instantiate the core LLMHarness once outside the conversation loop.
    try:
        harness = LLMHarness(
            model_name=target_model, use_entra_id=use_entra_id, console=console
        )
    except Exception as e:
        console.print(f"[red]❌ Core initialization pipeline broken: {e}[/red]")
        return

    while True:
        if force_menu:
            target_model, use_entra_id = show_menu(
                True, target_model, use_entra_id, console
            )
            save_config(target_model, use_entra_id)
            try:
                harness = LLMHarness(
                    model_name=target_model,
                    use_entra_id=use_entra_id,
                    console=console,
                )
            except Exception as e:
                console.print(f"[red]❌ Failed to reload harness layout: {e}[/red]")
                continue
            force_menu = False

        auth_type = "Entra ID" if use_entra_id else "API Key"
        os.system("cls" if os.name == "nt" else "clear")
        print_harness_screen(
            console, target_model, auth_type, len(current_chat_history)
        )
        console.print(f"      [grey50]Saved chat:[/grey50] [cyan]{session_id}[/cyan]\n")
        display_chat_history(current_chat_history, console)

        if show_interactive_loop:
            try:
                user_query = get_custom_prompt_input(
                    "\n\033[96mAsk anything (CTRL+D to submit, /help for commands) ❯ \033[0m"
                )
            except Exception:
                user_query = "exit"

            if not user_query:
                continue
            if user_query.lower() in ["/clear", "clear", "/reset", "reset"]:
                current_chat_history = []
                save_chat_session(session_id, current_chat_history, console)
                console.print(
                    "\n[bold green]🧹 This saved chat was cleared! "
                    "Token window reset to zero.[/bold green]"
                )
                await asyncio.sleep(1)
                continue
            if user_query.lower() in ["/help", "help", "?"]:
                show_help(console)
                continue
            if user_query.lower() in ["/chats", "chats", "history"]:
                session_id, current_chat_history = choose_chat_session(console)
                continue
            if user_query == "__TRIGGER_MENU__" or user_query.lower() in [
                "menu",
                "swap",
                "config",
            ]:
                force_menu = True
                continue
            if user_query.lower() in ["exit", "quit"]:
                console.print("[yellow]👋 Session safely terminated. Goodbye![/yellow]")
                break

        try:
            panel_reasoning, panel_answer, ui_group = llm_ui_panels(console)

            with Live(ui_group, console=console, refresh_per_second=10) as live_display:
                def handle_before_prompt():
                    try:
                        live_display.update("")
                        live_display.stop()
                    except Exception:
                        pass

                def handle_after_prompt():
                    try:
                        live_display.update(ui_group)
                        live_display.start()
                    except Exception:
                        pass

                harness.before_prompt = handle_before_prompt
                harness.after_prompt = handle_after_prompt
                safe_history = sanitize_history(
                    current_chat_history, max_messages=MAX_HISTORY_TURNS
                )
                async with harness.agent.run_stream(
                    user_query, message_history=safe_history
                ) as result:
                    async for current_data in result.stream_output():
                        try:
                            reasoning_accumulated = getattr(
                                current_data, "reasoning", ""
                            ).strip()
                            answer_accumulated = getattr(
                                current_data, "answer", ""
                            ).strip()

                            if reasoning_accumulated:
                                panel_reasoning.renderable = Markdown(
                                    reasoning_accumulated
                                )
                            if answer_accumulated:
                                panel_answer.renderable = Markdown(answer_accumulated)

                            live_display.update(ui_group)
                        except Exception:
                            continue

                    await result.get_output()
                    current_chat_history.extend(result.new_messages())
                    save_chat_session(session_id, current_chat_history, console)

            console.print("\n" + "─" * 70 + "\n")
            if not show_interactive_loop:
                break
            input("\033[90m👉 Press Enter to continue conversation step...\033[0m")

        except Exception as e:
            console.print(f"\n[red]❌ Execution terminated abnormally: {e}[/red]")
            input(
                "\033[93m👉 Press Enter to return to your current workspace interface...\033[0m"
            )
            if not show_interactive_loop:
                break


def cli():
    """Synchronous entry point that bootstraps the async main loop."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
