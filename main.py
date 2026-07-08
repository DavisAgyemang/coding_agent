from src.agent_memory_management.state_management import load_saved_config, load_chat_session, save_config, save_chat_session
from src.cli_ui.ui_config import show_menu, session_options, print_harness_screen, llm_ui_panels
import sys
import asyncio
import os
from rich.console import Console
from src.llm_harness.harness import LLMHarness
from src.general_tools.tooling import get_custom_prompt_input
from rich.markdown import Markdown

# =====================================================================
#  ENVIRONMENT ENFORCEMENT LAYER
# =====================================================================
if not os.environ.get("PYTHONUNBUFFERED"):
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)

console = Console()
session_id = "active_session"

async def main():
    config = load_saved_config(console)
    force_menu = (config is None)
    # prepare UI
    show_interactive_loop = True
    if not force_menu:
        target_model = config["model_name"]
        use_entra_id = config["use_entra_id"]

    # Pre-check if an active session exists on disk before entering the loop
    current_chat_history = load_chat_session(session_id=session_id, console=console) if not force_menu else []

    # sort out ui
    # choose menu
    target_model, use_entra_id = show_menu(force_menu, target_model, use_entra_id, console)
    save_config(target_model, use_entra_id)
    force_menu = False
    # user picks session options
    session_choice = session_options(console)
    if session_choice == '2':
        current_chat_history = load_chat_session(session_id, console)
    else:
        current_chat_history = []

    while True:
        if force_menu:
            target_model, use_entra_id = show_menu(True, target_model, use_entra_id, console)
            save_config(target_model, use_entra_id)
            force_menu = False

        try:
            harness = LLMHarness(model_name=target_model, use_entra_id=use_entra_id, console=console)
            # print harness loading screen
            print_harness_screen(console, target_model, use_entra_id, len(current_chat_history))

        except Exception as e:
            console.print(f"[red]❌ Core initialization pipeline broken: {e}[/red]")
            input("👉 Press Enter to return to menu choice setup...")
            force_menu = True
            continue

        if show_interactive_loop:
            try:
                user_query = get_custom_prompt_input("\033[96mAsk anything ❯ \033[0m")
            except Exception as input_err:
                user_query = "exit"

            if not user_query:
                continue

            if user_query == "__TRIGGER_MENU__" or user_query.lower() in ["menu", "swap", "config"]:
                force_menu = True
                continue

            if user_query.lower() in ["exit", "quit"]:
                console.print("[yellow]👋 Session safely terminated. Goodbye![/yellow]")
                break

        try:
            panel_reasoning, panel_answer, ui_group = llm_ui_panels(console)
            async with harness.agent.run_stream(user_query, message_history=current_chat_history) as result:
                async for current_data in result.stream_output():
                    try:
                        reasoning_accumulated = getattr(current_data, 'reasoning', '').strip()
                        answer_accumulated = getattr(current_data, 'answer', '').strip()
                        # return reasoning and answer
                        if reasoning_accumulated:
                            panel_reasoning.renderable = Markdown(reasoning_accumulated)
                        if answer_accumulated:
                            panel_answer.renderable = Markdown(answer_accumulated)
                    except Exception:
                        continue

                await result.get_output()
                current_chat_history = result.all_messages()
                save_chat_session(session_id, current_chat_history, console)
            os.system('cls' if os.name == 'nt' else 'clear')
            print_harness_screen(console, target_model, use_entra_id, len(current_chat_history))
            console.print(ui_group)
            console.print("\n" + "─" * 70 + "\n")
            if not show_interactive_loop:
                break
            else:
                input("\033[90m👉 Press Enter to continue conversation step...\033[0m")
        except Exception:
            console.print(f"\n[red]❌ Execution terminated abnormally: {e}[/red]")
            input("\033[93m👉 Press Enter to return to your current workspace interface...\033[0m")
            if not show_interactive_loop:
                break

if __name__ == "__main__":
    asyncio.run(main())