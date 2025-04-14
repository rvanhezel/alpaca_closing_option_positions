from unittest.mock import patch
from src.api.alpaca_api import AlpacaAPI
import pytest
import pandas as pd
from datetime import datetime
from src.api.api_utils import is_expiry_day, check_options_level


class MockOptionContract:
    def __init__(self, expiration_date):
        self.expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()

class TestApiUtils:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method."""
        self.timezone = "US/Eastern"
        self.api = AlpacaAPI()
        
    def test_fake_expiry_day(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        test_date = pd.Timestamp("2025-03-01", tz=self.timezone)

        with patch('src.api.alpaca_api.AlpacaAPI.get_option_contract_by_id', 
                  return_value=MockOptionContract(expiration_date="2025-03-01")), \
            pytest.MonkeyPatch.context() as mp:
                mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)

                assert is_expiry_day(self.api, "AAPL250620C00200000", self.timezone) == True

    def test_real_expiry_day(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        test_date = pd.Timestamp("2025-07-18", tz=self.timezone)

        with patch('src.api.alpaca_api.AlpacaAPI.get_option_contract_by_id', 
                  return_value=MockOptionContract(expiration_date="2025-07-18")), \
            pytest.MonkeyPatch.context() as mp:
                mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)

                assert is_expiry_day(self.api, "TSLA25071800200000", self.timezone) == True

    def test_not_expiry_day_before_expiry(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        test_date = pd.Timestamp("2025-01-01", tz=self.timezone)

        with patch('src.api.alpaca_api.AlpacaAPI.get_option_contract_by_id', 
                  return_value=MockOptionContract(expiration_date="2025-03-01")), \
            pytest.MonkeyPatch.context() as mp:
                mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)

                assert is_expiry_day(self.api, "AAPL250620C00200000", self.timezone) == False

    def test_not_expiry_day_after_expiry(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        test_date = pd.Timestamp("2025-05-02", tz=self.timezone)

        with patch('src.api.alpaca_api.AlpacaAPI.get_option_contract_by_id', 
                  return_value=MockOptionContract(expiration_date="2025-03-01")), \
            pytest.MonkeyPatch.context() as mp:
                mp.setattr('pandas.Timestamp.now', lambda tz=None: test_date)

                assert is_expiry_day(self.api, "AAPL250620C00200000", self.timezone) == False

    def test_level_3_options_approved(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        with patch('src.api.alpaca_api.AlpacaAPI.options_approved_level', 
                  return_value=3), \
            patch('src.api.alpaca_api.AlpacaAPI.options_trading_level', 
                  return_value=3):
                assert check_options_level(self.api, 3) == True

    def test_level_3_options_not_approved(self):
        """Test is_expiry_day function with various dates"""
        # Set a fixed date in the middle of a contract period
        with patch('src.api.alpaca_api.AlpacaAPI.options_approved_level', 
                  return_value=2), \
            patch('src.api.alpaca_api.AlpacaAPI.options_trading_level', 
                  return_value=3):
                assert check_options_level(self.api, 3) == False



