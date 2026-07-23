"""
QuantBIST RC5
Watchlist Repository
"""

from __future__ import annotations

import json
from pathlib import Path

from core.infrastructure.logger import get_logger


logger = get_logger(__name__)


# =====================================================
# CONFIG
# =====================================================

WATCHLIST_FILE = Path(
    "data/watchlist.json"
)



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


        data = json.loads(

            WATCHLIST_FILE.read_text(
                encoding="utf-8"
            )

        )


        if not isinstance(
            data,
            dict,
        ):

            logger.warning(
                "Invalid watchlist format."
            )

            return {}


        return data



    except json.JSONDecodeError:

        logger.exception(
            "Watchlist JSON corrupted."
        )

        return {}



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
