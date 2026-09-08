from src.agent_memory_management.state_management import load_saved_config, load_chat_session, save_config, save_chat_session
from src.cli_ui.ui_config import show_menu, session_options, print_harness_screen, llm_ui_panels, display_chat_history, show_help
import sys
import asyncio
import os
from rich.console import Console
from src.llm_harness.harness import LLMHarness
from src.general_tools.tooling import get_custom_prompt_input
from rich.markdown import Markdown
from rich.live import Live
from typing import List
from src.general_tools.sanitise_chat import sanitize_history
# =====================================================================
#  ENVIRONMENT ENFORCEMENT LAYER
# =====================================================================
if not os.environ.get("PYTHONUNBUFFERED"):
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)

console = Console()
session_id = "active_session"
MAX_HISTORY_TURNS = 12  # Keeps context focused while preventing token bloat




async def main():
    config = load_saved_config(console)
    force_menu = (config is None)
    show_interactive_loop = True

    target_model = config["model_name"] if not force_menu else None
    use_entra_id = config["use_entra_id"] if not force_menu else True
    auth_type = "Entra ID" if use_entra_id is True else "API Key"

    # 1. Select menu options
    target_model, use_entra_id = show_menu(force_menu, target_model, use_entra_id, console)
    save_config(target_model, use_entra_id)
    force_menu = False

    # 2. Establish context memory session
    session_choice = session_options(console)
    if session_choice == '2':
        current_chat_history = load_chat_session(session_id, console)
    else:
        current_chat_history = []

    # 3. Instantiate the core LLMHarness ONCE outside the loop to prevent initialization reset cycles
    try:
        harness = LLMHarness(model_name=target_model, use_entra_id=use_entra_id, console=console)
    except Exception as e:
        console.print(f"[red]❌ Core initialization pipeline broken: {e}[/red]")
        return

    # =================================================================
    # 🔄 THE RECONFIGURED APPLICATION CONVERSATION ENGINE
    # =================================================================
    while True:
        if force_menu:
            target_model, use_entra_id = show_menu(True, target_model, use_entra_id, console)
            save_config(target_model, use_entra_id)
            try:
                harness = LLMHarness(model_name=target_model, use_entra_id=use_entra_id, console=console)
            except Exception as e:
                console.print(f"[red]❌ Failed to reload harness layout: {e}[/red]")
                continue
            force_menu = False

        #  Draw the complete persistent display layout before demanding input
        os.system('cls' if os.name == 'nt' else 'clear')
        print_harness_screen(console, target_model, auth_type, len(current_chat_history))
        display_chat_history(current_chat_history, console)

        #  Ask the user their next question right below the persistent history stack
        if show_interactive_loop:
            try:
                user_query = get_custom_prompt_input("\n\033[96mAsk anything (CTRL+D to submit, /help for commands) ❯ \033[0m")
            except Exception:
                user_query = "exit"

            if not user_query:
                continue
            if user_query.lower() in ["/clear", "clear", "/reset", "reset"]:
                current_chat_history = []
                save_chat_session(session_id, current_chat_history, console)
                console.print("\n[bold green]🧹 Session memory cleared! Token window reset to zero.[/bold green]")
                await asyncio.sleep(1)
                continue
            if user_query.lower() in ["/help", "help", "?"]:
                show_help(console)
                continue



            if user_query == "__TRIGGER_MENU__" or user_query.lower() in ["menu", "swap", "config"]:
                force_menu = True
                continue

            if user_query.lower() in ["exit", "quit"]:
                console.print("[yellow]👋 Session safely terminated. Goodbye![/yellow]")
                break

        # Process live stream panels cleanly underneath the drawn canvas

        try:
            panel_reasoning, panel_answer, ui_group = llm_ui_panels(console)

            with Live(ui_group, console=console, refresh_per_second=10) as live_display:
                # 🌟 FIXED: Erase the layout panels by updating to an empty layout before stopping
                def handle_before_prompt():
                    try:
                        # 1. Update the live screen to display absolutely nothing
                        live_display.update("")
                        # 2. Stop the live display window context
                        live_display.stop()
                    except Exception:
                        pass

                def handle_after_prompt():
                    try:
                        # 1. Put your active panels back as the target layout renderable
                        live_display.update(ui_group)
                        # 2. Re-start the dynamic display window cleanly
                        live_display.start()
                    except Exception:
                        pass

                # Attach the improved cleanup hooks to your harness
                harness.before_prompt = handle_before_prompt
                harness.after_prompt = handle_after_prompt
                # recent_history = current_chat_history[-10:] if len(current_chat_history) > 10 else current_chat_history
                safe_history = sanitize_history(current_chat_history, max_messages=MAX_HISTORY_TURNS)
                async with harness.agent.run_stream(user_query, message_history=safe_history) as result:
                    async for current_data in result.stream_output():
                        try:
                            reasoning_accumulated = getattr(current_data, 'reasoning', '').strip()
                            answer_accumulated = getattr(current_data, 'answer', '').strip()

                            if reasoning_accumulated:
                                panel_reasoning.renderable = Markdown(reasoning_accumulated)
                            if answer_accumulated:
                                panel_answer.renderable = Markdown(answer_accumulated)

                            live_display.update(ui_group)
                        except Exception:
                            continue

                    await result.get_output()
                    # current_chat_history = result.all_messages()
                    #  Append ONLY the new messages from this specific turn to your complete infinite history
                    current_chat_history.extend(result.new_messages())
                    save_chat_session(session_id, current_chat_history, console)

            # 👇 STEP D: Wait for user step verification acknowledgment before rendering loop cycle
            console.print("\n" + "─" * 70 + "\n")
            if not show_interactive_loop:
                break
            else:
                input("\033[90m👉 Press Enter to continue conversation step...\033[0m")

        except Exception as e:
            console.print(f"\n[red]❌ Execution terminated abnormally: {e}[/red]")
            input("\033[93m👉 Press Enter to return to your current workspace interface...\033[0m")
            if not show_interactive_loop:
                break

def cli():
    """Synchronous entry point that bootstraps your async main loop."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()