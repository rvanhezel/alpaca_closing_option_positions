import pytest
import pandas as pd
from src.portfolio.portfolio_manager import PortfolioManager
import os
from src.configuration import Configuration
from unittest.mock import patch


class TestPortfolioManager:

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method."""
        self.cfg = Configuration(os.path.join(os.getcwd(), 
                                        "test", 
                                        "test_portfolio_manager", 
                                        "test_run.cfg"))
        self.portfolio_manager = PortfolioManager(self.cfg, None)

        self.cfg_tsla = Configuration(os.path.join(os.getcwd(), 
                                        "test", 
                                        "test_portfolio_manager", 
                                        "test_run_tsla.cfg"))
        self.portfolio_manager_tsla = PortfolioManager(self.cfg_tsla, None)

    def test_populate_from_csv(self):
        """Test populate_from_csv function"""

        with patch('os.path.join', 
                  return_value=os.path.join("test", "test_portfolio_manager", "test_data.csv")):

            self.portfolio_manager.populate_from_csv()

            assert self.portfolio_manager.closed_buckets.empty == False
            assert len(self.portfolio_manager.closed_buckets) == 2
            assert self.portfolio_manager.starting_idx == 2

    def test_populate_from_csv_empty(self):
        """Test populate_from_csv function"""

        with patch('os.path.join', 
                  return_value=os.path.join("test", "test_portfolio_manager", "test_data.csv")):

            self.portfolio_manager_tsla.populate_from_csv()

            assert self.portfolio_manager_tsla.closed_buckets.empty == True
            assert len(self.portfolio_manager_tsla.closed_buckets) == 0
            assert self.portfolio_manager_tsla.starting_idx == 0


