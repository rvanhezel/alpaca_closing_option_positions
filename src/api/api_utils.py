import pandas as pd
from src.api.alpaca_api import AlpacaAPI


def is_expiry_day(api: AlpacaAPI, instrument_id: str, timezone: str) -> bool:
    """Check if the option is expiring today"""
    now = pd.Timestamp.now(tz=timezone)
    expiry_date = api.get_option_contract_by_id(instrument_id).expiration_date
    if now.date() == expiry_date:
        return True
    else:
        return False
