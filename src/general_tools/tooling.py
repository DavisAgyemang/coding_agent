import os
import sys


if os.name != 'nt':
    import tty
    import termios

def get_custom_prompt_input(prompt_text: str) -> str:
    if os.name == 'nt':
        res = input(prompt_text).strip()
        if res.lower() in ['menu', 'swap']: return "__TRIGGER_MENU__"
        return res

    if not sys.stdin.isatty():
        try:
            return input(prompt_text).strip()
        except (KeyboardInterrupt, EOFError):
            return "exit"

    print(prompt_text, end="", flush=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    input_buffer = []

    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            ch = sys.stdin.read(1)
            if not ch: continue
            ord_ch = ord(ch)
            if ord_ch in [10, 13]:
                break
            elif ord_ch in [127, 8]:
                if input_buffer:
                    input_buffer.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ord_ch == 3:
                raise KeyboardInterrupt
            else:
                input_buffer.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    final_str = "".join(input_buffer).strip()
    print()
    return final_str
