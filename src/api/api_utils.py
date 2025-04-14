import pandas as pd
from src.api.alpaca_api import AlpacaAPI
from typing import Optional


def is_expiry_day(api: AlpacaAPI, instrument_id: str, timezone: str) -> bool:
    """Check if the option is expiring today.
    
    Args:
        api (AlpacaAPI): The Alpaca API instance
        instrument_id (str): The ID of the option contract
        timezone (str): The timezone to use for date comparison
        
    Returns:
        bool: True if the option expires today, False otherwise
        
    Raises:
        ValueError: If the instrument_id is invalid or the contract cannot be found
    """
    now = pd.Timestamp.now(tz=timezone)
    expiry_date = api.get_option_contract_by_id(instrument_id).expiration_date
    if now.date() == expiry_date:
        return True
    else:
        return False
    
def check_options_level(api: AlpacaAPI, level: int) -> bool:
    """Check if the options trading level meets or exceeds the required level.
    
    Args:
        api (AlpacaAPI): The Alpaca API instance
        level (int): The minimum required options trading level
        
    Returns:
        bool: True if both approved and current trading levels meet or exceed the required level,
              False otherwise
              
    Raises:
        ConnectionError: If unable to connect to the API
        ValueError: If the level parameter is invalid
    """
    return api.options_approved_level() >= level and api.options_trading_level() >= level

