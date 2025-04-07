from typing import Optional
import pandas as pd


class OrderStatus:
    def __init__(self,
                 order_id: int,
                 status: str,
                 filled: int,
                 remaining: int,
                 avg_fill_price: Optional[float] = None,
                 last_fill_price: Optional[float] = None,
                 parent_id: Optional[int] = None):
        """Initialize an OrderStatus
        
        Args:
            order_id (int): ID of the order this status is for
            status (str): Current status of the order
            filled (int): Number of contracts/shares filled
            remaining (int): Number of contracts/shares remaining
            avg_fill_price (float, optional): Average fill price
            last_fill_price (float, optional): Last fill price
            parent_id (int, optional): ID of parent order
        """
        self.order_id = order_id
        self.status = status
        self.filled = filled
        self.remaining = remaining
        self.avg_fill_price = avg_fill_price
        self.last_fill_price = last_fill_price
        self.parent_id = parent_id
        self.last_modified = pd.Timestamp.now()

    @classmethod
    def from_dict(cls, data: dict) -> 'OrderStatus':
        """Create an OrderStatus instance from a dictionary
        
        Args:
            data (dict): Dictionary containing order status data
            
        Returns:
            OrderStatus: New OrderStatus instance
        """
        return cls(
            order_id=data.get('order_id'),
            status=data.get('status'),
            filled=data.get('filled'),
            remaining=data.get('remaining'),
            avg_fill_price=data.get('avg_fill_price'),
            last_fill_price=data.get('last_fill_price'),
            parent_id=data.get('parent_id')
        )

    def to_dict(self) -> dict:
        """Convert the OrderStatus to a dictionary
        
        Returns:
            dict: Dictionary representation of the OrderStatus
        """
        return {
            'order_id': self.order_id,
            'status': self.status,
            'filled': self.filled,
            'remaining': self.remaining,
            'avg_fill_price': self.avg_fill_price,
            'last_fill_price': self.last_fill_price,
            'parent_id': self.parent_id,
            'last_modified': self.last_modified.isoformat()
        }

    def __str__(self) -> str:
        """String representation of the OrderStatus
        
        Returns:
            str: Formatted string showing order status details
        """
        fill_str = f"Filled: {self.filled}/{self.filled + self.remaining}"
        price_str = f" @ {self.avg_fill_price}" if self.avg_fill_price else ""
        return f"Order {self.order_id}: {self.status} - {fill_str}{price_str}" 