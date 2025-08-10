import base64
import os
import config
from io import BytesIO
from PIL import Image
from termcolor import colored


def display_image(data: str, display_name: str, width: int = 30) -> bool:
    """
    Displays an image in terminal using various methods
    Returns True if successful, False if fell back to text
    """
    try:
        img_data = base64.b64decode(data)
        img = Image.open(BytesIO(img_data))

        # Try Kitty terminal first
        if "TERM" in os.environ and "kitty" in os.environ["TERM"].lower():
            from base64 import standard_b64encode

            img.thumbnail((width * 10, width * 10))
            with BytesIO() as output:
                img.save(output, format="PNG")
                print(
                    f"\033_Ga=T,f=100,t=d;{standard_b64encode(
                        output.getvalue()).decode()}\033\\"
                )
            return True

        # Try iTerm2
        elif "ITERM_PROFILE" in os.environ:
            from base64 import standard_b64encode

            print(
                f"\033]1337;File=inline=1;width={width}px;preserveAspectRatio=1:{
                    standard_b64encode(img_data).decode()}\a"
            )
            return True

        # Fallback to ASCII art
        else:
            from pyfiglet import Figlet

            f = Figlet(font="small")
            print(colored(f.renderText(display_name[:3]), "cyan"))
            return False

    except Exception as e:
        if config.verbose_mode:
            print(f"Failed to display image: {e}")
        return False
