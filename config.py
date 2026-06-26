from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHAT_ID: int = int(os.getenv("CHAT_ID", "0"))

DEBUG: bool = False
VERSION: str = "4.0.0"
APP_NAME: str = "QuantBIST RC4"

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN bulunamadı."
    )