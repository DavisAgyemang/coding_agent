import os
import sys

if os.name != 'nt':
    import termios
    import tty


def get_custom_prompt_input(prompt_text: str) -> str:
    if os.name == 'nt':
        res = input(prompt_text).strip()
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        res = "\n".join(lines).strip()
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

            # Detect Ctrl+D (ASCII Code 4) to submit
            if ord_ch == 4:
                break

            # Detect Enter / Return Keys (Code 10 or 13) from manual typing
            elif ord_ch in [10, 13]:
                input_buffer.append("\n")
                # 🌟 FIXED: Force carriage return + line feed for manual enters
                sys.stdout.write("\r\n")
                sys.stdout.flush()

            # Detect Backspace
            elif ord_ch in [127, 8]:
                if input_buffer:
                    removed = input_buffer.pop()
                    if removed == "\n":
                        sys.stdout.write("\033[A\033[K")
                    else:
                        sys.stdout.write("\b \b")
                    sys.stdout.flush()

            # Detect Ctrl+C
            elif ord_ch == 3:
                raise KeyboardInterrupt

            # Regular text typing or block pasting stream
            else:
                input_buffer.append(ch)
                # 🌟 FIXED: Intercept incoming clipboard newlines and attach '\r'
                if ch == "\n" or ord_ch in [10, 13]:
                    sys.stdout.write("\r\n")
                else:
                    sys.stdout.write(ch)
                sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    final_str = "".join(input_buffer).strip()
    print()

    if final_str.lower() in ['menu', 'swap']:
        return "__TRIGGER_MENU__"

    return final_str