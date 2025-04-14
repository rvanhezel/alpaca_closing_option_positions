import pytest
import pandas as pd
import pytz
import os
from unittest.mock import patch
from src.portfolio.portfolio_manager import PortfolioManager
from src.trading_session_manager import TradingSessionManager


class TestTradingSessionManager:

    @pytest.fixture
    def trading_session_manager(self):
        """Create a TradingSessionManager instance with trading hours from run.cfg"""
        return TradingSessionManager(
            trading_start_time="0930",  
            trading_end_time="1600",   
            timezone="US/Central")

    def test_is_trading_day(self, trading_session_manager: TradingSessionManager):
        """Test is_trading_day function with various dates"""
        et_tz = trading_session_manager.timezone
        
        monday = pd.Timestamp("2025-03-17", tz=et_tz)  # Monday
        assert trading_session_manager.is_trading_day(monday) == True
        
        tuesday = pd.Timestamp("2025-03-18", tz=et_tz)  # Tuesday
        assert trading_session_manager.is_trading_day(tuesday) == True
        
        wednesday = pd.Timestamp("2025-03-19", tz=et_tz)  # Wednesday
        assert trading_session_manager.is_trading_day(wednesday) == True

        thursday = pd.Timestamp("2025-03-20", tz=et_tz)  # Thursday
        assert trading_session_manager.is_trading_day(thursday) == True

        friday = pd.Timestamp("2025-03-21", tz=et_tz)  # Friday
        assert trading_session_manager.is_trading_day(friday) == True

        saturday = pd.Timestamp("2025-03-22", tz=et_tz)  # Saturday
        assert trading_session_manager.is_trading_day(saturday) == False

        sunday_morning = pd.Timestamp("2025-03-23 09:00", tz=et_tz)  # Sunday
        assert trading_session_manager.is_trading_day(sunday_morning) == False

        sunday_afternoon = pd.Timestamp("2025-03-23 18:00", tz=et_tz)  # Sunday
        assert trading_session_manager.is_trading_day(sunday_afternoon) == False

        sunday_evening = pd.Timestamp("2025-03-23 21:00", tz=et_tz)  # Sunday
        assert trading_session_manager.is_trading_day(sunday_evening) == False
        
        christmas = pd.Timestamp("2025-12-25", tz=et_tz)  # Christmas
        assert trading_session_manager.is_trading_day(christmas) == False
        
        new_year = pd.Timestamp("2025-01-01", tz=et_tz)  # New Year's Day
        assert trading_session_manager.is_trading_day(new_year) == False

    def test_is_trading_hours(self, trading_session_manager: TradingSessionManager):
        """Test is_trading_hours function with various times"""
        et_tz = trading_session_manager.timezone
        
        # Test during trading hours (10:00 PM ET)
        trading_time = pd.Timestamp("2025-03-18 22:00", tz=et_tz)  # Tuesday 10:00 PM ET
        assert trading_session_manager.is_trading_hours(trading_time) == False
        
        # Test during trading hours (2:00 PM ET)
        trading_time = pd.Timestamp("2025-03-18 14:00", tz=et_tz)  # Tuesday 2:00 PM ET
        assert trading_session_manager.is_trading_hours(trading_time) == True
        
        # Test outside trading hours (5:00 PM ET)
        non_trading_time = pd.Timestamp("2025-03-18 17:00", tz=et_tz)  # Tuesday 5:00 PM ET
        assert trading_session_manager.is_trading_hours(non_trading_time) == False
        
        # Test outside trading hours (8:00 PM ET)
        non_trading_time = pd.Timestamp("2025-03-18 20:00", tz=et_tz)  # Tuesday 8:00 PM ET
        assert trading_session_manager.is_trading_hours(non_trading_time) == False
        
        # Test exactly at trading start (9:00 PM ET)
        start_time = pd.Timestamp("2025-03-18 21:00", tz=et_tz)  # Tuesday 9:00 PM ET
        assert trading_session_manager.is_trading_hours(start_time) == False
        
        # Test exactly at trading end (4:00 PM ET)
        end_time = pd.Timestamp("2025-03-18 16:00", tz=et_tz)  # Tuesday 4:00 PM ET
        assert trading_session_manager.is_trading_hours(end_time) == False

    def test_is_trading_hours_overnight(self, trading_session_manager: TradingSessionManager):
        """Test is_trading_hours function with overnight trading hours"""
        et_tz = trading_session_manager.timezone
        
        # Test during overnight trading (2:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 02:00", tz=et_tz)  # Monday 2:00 AM ET
        assert trading_session_manager.is_trading_hours(overnight_time) == False
        
        # Test during overnight trading (4:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 04:00", tz=et_tz)  # Monday 4:00 AM ET
        assert trading_session_manager.is_trading_hours(overnight_time) == False
        
        # Test during overnight trading (6:00 AM ET)
        overnight_time = pd.Timestamp("2025-03-17 06:00", tz=et_tz)  # Monday 6:00 AM ET
        assert trading_session_manager.is_trading_hours(overnight_time) == False

    def test_is_trading_hours_edge_cases(self, trading_session_manager: TradingSessionManager):
        """Test is_trading_hours function with various times"""
        et_tz = trading_session_manager.timezone
        
        # Test during trading hours (10:00 PM ET)
        open_trading_time = pd.Timestamp("2025-03-18 09:30", tz=et_tz)  # Tuesday 10:00 PM ET
        assert trading_session_manager.is_trading_hours(open_trading_time) == True
        
        # Test during trading hours (2:00 PM ET)
        close_trading_time = pd.Timestamp("2025-03-18 16:00", tz=et_tz)  # Tuesday 2:00 PM ET
        assert trading_session_manager.is_trading_hours(close_trading_time) == False


        

