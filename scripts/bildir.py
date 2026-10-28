"""Send a short message to the QuantBIST Telegram chat (used by the PC updater).

    python bildir.py "mesaj metni"
    python bildir.py --file ozet.txt

Uses the project's own sender and .env (BOT_TOKEN, CHAT_ID); prints the
text too, so a failed send still leaves it in the task log.
"""

import sys
from pathlib import Path

PROJECT = Path(r"C:\Projeler\QuantBIST")
sys.path.insert(0, str(PROJECT))

from core.infrastructure.settings import require_bot_settings  # noqa: E402
from core.reports.daily import send_telegram  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--file":
        text = Path(argv[1]).read_text(encoding="utf-8")
    else:
        text = " ".join(argv)
    if not text.strip():
        print("bildir: boş mesaj", file=sys.stderr)
        return 2
    print(text)
    settings = require_bot_settings()
    send_telegram("🤖 Otomasyon\n" + text, settings.bot_token, settings.chat_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
