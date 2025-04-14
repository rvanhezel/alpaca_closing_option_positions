import logging
import pandas as pd
import holidays
import pytz
import time
from typing import Optional


class TradingSessionManager:
    """TradingSessionManager handles the logic for determining valid trading sessions.
    
    This class is responsible for:
    - Managing trading hours and determining if current time is within trading window
    - Checking if a given day is a valid trading day (accounting for weekends and holidays)
    - Providing timezone-aware session management for consistent trading schedules
    - Handling end-of-day market close logic and position management
    
    The trading session logic handles overnight sessions that span across days,
    as well as regular market hour sessions. It accounts for US holidays and
    weekend trading restrictions. It also manages the orderly closing of positions
    and cancellation of orders as market close approaches.
    """
    
    def __init__(self, timezone: str, trading_start_time: str, trading_end_time: str) -> None:
        """Initialize the trading session manager
        
        Args:
            timezone (str): Timezone for trading hours (e.g. 'America/New_York')
            trading_start_time (str): Start time in HHMM format (e.g. '2100' for 9:00 PM)
            trading_end_time (str): End time in HHMM format (e.g. '1600' for 4:00 PM)
        """
        self.timezone = timezone
        self.trading_start = pd.to_datetime(trading_start_time, format='%H%M').tz_localize(self.timezone).time()
        self.trading_end = pd.to_datetime(trading_end_time, format='%H%M').tz_localize(self.timezone).time()
    
    def is_trading_hours(self, now: pd.Timestamp) -> bool:
        """Check if current time is within trading hours
        
        Args:
            now (pd.Timestamp): Current timestamp to check
            
        Returns:
            bool: True if within trading hours, False otherwise
        """
        logging.debug(f"TradingSessionManager: Checking trading time. Current timestamp: {now}")
        current_time = now.time()
        
        if self.trading_start < self.trading_end:
            return self.trading_start <= current_time < self.trading_end
        else:
            return current_time >= self.trading_start or current_time < self.trading_end
            
    def is_trading_day(self, now_timestamp: pd.Timestamp) -> bool:
        """Check if today is a trading day (Sunday through Friday)
        
        Args:
            now_timestamp (pd.Timestamp): Current timestamp to check
            
        Returns:
            bool: True if it's a trading day, False otherwise
        """
        logging.debug(f"TradingSessionManager: Checking trading day. Current timestamp: {now_timestamp}")
        us_holidays = holidays.UnitedStates()
        weekday = now_timestamp.weekday()

        if now_timestamp.date() in us_holidays:
            return False
        
        # Monday through Friday (0-4)
        elif 0 <= weekday <= 4:
            return True
            
        else:
            return False 
        
    def perform_eod_close(self, 
                         now: pd.Timestamp, 
                         eod_exit_time: str, 
                         market_close_time: str) -> bool:
        """Perform end of day checks and handle market close procedures.
        
        Args:
            now (pd.Timestamp): Current timestamp
            eod_exit_time (str): Time to start EOD procedures in HHMM format
            market_close_time (str): Market close time in HHMM format
            
        Returns:
            bool: True if EOD procedures were performed, False otherwise
        """
        eod_cutoff = pd.Timestamp(
                now.year, 
                now.month, 
                now.day, 
                int(eod_exit_time[:2]),           
                int(eod_exit_time[2:]),           
                tz=self.timezone)
        
        market_close_time = pd.Timestamp(
                now.year, 
                now.month, 
                now.day, 
                int(market_close_time[:2]),           
                int(market_close_time[2:]),           
                tz=self.timezone)

        if market_close_time >= now >= eod_cutoff:
            logging.info(f"Current time: {now} - End of day approaching - Performing EOD checks")
            
            # Define EOD logic here
            logging.info(f"Currently no EOD checks to perform")

            seconds_until_close = (market_close_time - now).total_seconds()
            logging.info(f"Sleeping for {seconds_until_close} seconds until market close")
            time.sleep(seconds_until_close)
            return True
        
        return False
