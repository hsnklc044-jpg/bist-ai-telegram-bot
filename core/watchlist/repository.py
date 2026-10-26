"""
QuantBIST RC5
Watchlist Repository
"""

from __future__ import annotations

import json

from core.config.paths import WATCHLIST_FILE
from core.infrastructure.exceptions import PersonalFileError
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)


# =====================================================
# CONFIG
# =====================================================


# =====================================================
# LOAD
# =====================================================

def load_watchlist() -> dict:
    """
    Load user watchlist data.
    """

    try:

        if not WATCHLIST_FILE.exists():

            logger.warning(
                "Watchlist file missing. Creating default."
            )


            WATCHLIST_FILE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )


            WATCHLIST_FILE.write_text(
                "{}",
                encoding="utf-8",
            )


        text = WATCHLIST_FILE.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            # never replaced by an empty list: the next save would lose every symbol
            raise PersonalFileError(WATCHLIST_FILE, f"JSON bozuk ({exc.msg})", line=exc.lineno) from exc
        if not isinstance(data, dict):
            raise PersonalFileError(WATCHLIST_FILE, "beklenen yapı değil (kullanıcı listesi olmalı)")
        return data

    except PersonalFileError:
        logger.error("Watchlist file is damaged; left as it is.")
        raise

    except Exception as exc:

        logger.exception(
            "Watchlist loading failed."
        )

        raise exc




# =====================================================
# SAVE
# =====================================================

def save_watchlist(
    data: dict,
) -> None:
    """
    Save watchlist data.
    """

    try:

        WATCHLIST_FILE.parent.mkdir(

            parents=True,

            exist_ok=True,

        )


        WATCHLIST_FILE.write_text(

            json.dumps(

                data,

                indent=4,

                ensure_ascii=False,

            ),

            encoding="utf-8",

        )


        logger.info(
            "Watchlist saved."
        )


    except Exception as exc:

        logger.exception(
            "Watchlist save failed."
        )

        raise exc



# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "load_watchlist",

    "save_watchlist",

]
