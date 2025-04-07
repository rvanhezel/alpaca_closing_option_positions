from typing import Optional
import pandas as pd


class Instrument:
    def __init__(self,
                 symbol: str,
                 exchange: str,
                 currency: str):
        """Initialize an Instrument
        
        Args:
            symbol (str): The symbol of the instrument
            exchange (str): The exchange where the instrument is traded
            currency (str): The currency of the instrument
        """
        self.symbol = symbol
        self.exchange = exchange
        self.currency = currency

    @classmethod
    def from_dict(cls, data: dict) -> 'Instrument':
        """Create an Instrument instance from a dictionary
        
        Args:
            data (dict): Dictionary containing instrument data
            
        Returns:
            Instrument: New Instrument instance
        """
        return cls(
            symbol=data.get('symbol'),
            exchange=data.get('exchange'),
            currency=data.get('currency')
        )

    def to_dict(self) -> dict:
        """Convert the Instrument to a dictionary
        
        Returns:
            dict: Dictionary representation of the Instrument
        """
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'currency': self.currency
        }

    def __str__(self) -> str:
        """String representation of the Instrument
        
        Returns:
            str: Formatted string showing instrument details
        """
        return f"{self.symbol} {self.exchange} {self.currency}"
    

class EuropeanOption(Instrument):
    def __init__(self,
                 symbol: str,
                 exchange: str,
                 currency: str,
                 expiry: str,
                 strike: float,
                 right: str,
                 multiplier: str = "100"):
        """Initialize a European Option
        
        Args:
            symbol (str): The symbol of the underlying
            exchange (str): The exchange where the option is traded
            currency (str): The currency of the option
            expiry (str): Expiration date (YYYYMMDD)
            strike (float): Strike price
            right (str): Put/Call
            multiplier (str): Contract multiplier (default: 100)
        """
        super().__init__(symbol, exchange, currency)
        self.expiry = expiry
        self.strike = strike
        self.right = right
        self.multiplier = multiplier

    @classmethod
    def from_dict(cls, data: dict) -> 'EuropeanOption':
        """Create a EuropeanOption instance from a dictionary
        
        Args:
            data (dict): Dictionary containing option data
            
        Returns:
            EuropeanOption: New EuropeanOption instance
        """
        return cls(
            symbol=data.get('symbol'),
            exchange=data.get('exchange'),
            currency=data.get('currency'),
            expiry=data.get('expiry'),
            strike=data.get('strike'),
            right=data.get('right'),
            multiplier=data.get('multiplier', '100')
        )

    def to_dict(self) -> dict:
        """Convert the EuropeanOption to a dictionary
        
        Returns:
            dict: Dictionary representation of the EuropeanOption
        """
        data = super().to_dict()
        data.update({
            'expiry': self.expiry,
            'strike': self.strike,
            'right': self.right,
            'multiplier': self.multiplier
        })
        return data

    def __str__(self) -> str:
        """String representation of the EuropeanOption
        
        Returns:
            str: Formatted string showing option details
        """
        base_str = super().__str__()
        return f"OPT {base_str} {self.expiry} {self.strike} {self.right}"


class AmericanOption(Instrument):
    def __init__(self,
                 symbol: str,
                 exchange: str,
                 currency: str,
                 expiry: str,
                 strike: float,
                 right: str,
                 multiplier: str = "100"):
        """Initialize an American Option
        
        Args:
            symbol (str): The symbol of the underlying
            exchange (str): The exchange where the option is traded
            currency (str): The currency of the option
            expiry (str): Expiration date (YYYYMMDD)
            strike (float): Strike price
            right (str): Put/Call
            multiplier (str): Contract multiplier (default: 100)
        """
        super().__init__(symbol, exchange, currency)
        self.expiry = expiry
        self.strike = strike
        self.right = right
        self.multiplier = multiplier

    @classmethod
    def from_dict(cls, data: dict) -> 'AmericanOption':
        """Create an AmericanOption instance from a dictionary
        
        Args:
            data (dict): Dictionary containing option data
            
        Returns:
            AmericanOption: New AmericanOption instance
        """
        return cls(
            symbol=data.get('symbol'),
            exchange=data.get('exchange'),
            currency=data.get('currency'),
            expiry=data.get('expiry'),
            strike=data.get('strike'),
            right=data.get('right'),
            multiplier=data.get('multiplier', '100')
        )

    def to_dict(self) -> dict:
        """Convert the AmericanOption to a dictionary
        
        Returns:
            dict: Dictionary representation of the AmericanOption
        """
        data = super().to_dict()
        data.update({
            'expiry': self.expiry,
            'strike': self.strike,
            'right': self.right,
            'multiplier': self.multiplier
        })
        return data

    def __str__(self) -> str:
        """String representation of the AmericanOption
        
        Returns:
            str: Formatted string showing option details
        """
        base_str = super().__str__()
        return f"OPT {base_str} {self.expiry} {self.strike} {self.right}"


class Future(Instrument):
    def __init__(self,
                 symbol: str,
                 exchange: str,
                 currency: str,
                 expiry: str,
                 multiplier: str):
        """Initialize a Future
        
        Args:
            symbol (str): The symbol of the future
            exchange (str): The exchange where the future is traded
            currency (str): The currency of the future
            expiry (str): Expiration date (YYYYMMDD)
            multiplier (str): Contract multiplier
        """
        super().__init__(symbol, exchange, currency)
        self.expiry = expiry
        self.multiplier = multiplier

    @classmethod
    def from_dict(cls, data: dict) -> 'Future':
        """Create a Future instance from a dictionary
        
        Args:
            data (dict): Dictionary containing future data
            
        Returns:
            Future: New Future instance
        """
        return cls(
            symbol=data.get('symbol'),
            exchange=data.get('exchange'),
            currency=data.get('currency'),
            expiry=data.get('expiry'),
            multiplier=data.get('multiplier')
        )

    def to_dict(self) -> dict:
        """Convert the Future to a dictionary
        
        Returns:
            dict: Dictionary representation of the Future
        """
        data = super().to_dict()
        data.update({
            'expiry': self.expiry,
            'multiplier': self.multiplier
        })
        return data

    def __str__(self) -> str:
        """String representation of the Future
        
        Returns:
            str: Formatted string showing future details
        """
        base_str = super().__str__()
        return f"FUT {base_str} {self.expiry}" 