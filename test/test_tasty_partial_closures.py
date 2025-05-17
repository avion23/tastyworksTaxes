import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyPartialClosures:
    def test_partial_closure_amounts(self):
        """Test correct prorating of values in partial position closures"""
        t = Tasty()
        
        # Add opening position: 100 shares at $10 = $1000 with $5 fees
        t.addPosition(Transaction.fromString("01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,100,,,,10,5,-1000,Bought 100 XYZ @ 10,Individual...39"))
        position = Transaction(t.positions.squeeze())
        assert position.getQuantity() == 100
        assert position["Amount"] == -1000
        assert position["Fees"] == 5
        
        # Close 50% at $12 = $600 with $3 fees
        t.addPosition(Transaction.fromString("01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,50,,,,12,3,600,Sold 50 XYZ @ 12,Individual...39"))
        
        # Verify remaining position
        position = Transaction(t.positions.squeeze())
        assert position.getQuantity() == 50
        assert position["Amount"] == -500  # 50% of original cost
        assert position["Fees"] == 2.5     # 50% of original fees
        
        # Verify closed trade
        trade = Transaction(t.closedTrades.squeeze())
        assert trade["Quantity"] == 50
        assert trade["Amount"] == 100      # (600 - 500): correct P/L
        assert trade["Fees"] == 5.5        # (2.5 + 3): correct fee allocation
    
    def test_multiple_partial_closures(self):
        """Test that consecutive partial closures maintain proper accounting"""
        t = Tasty()
        
        # Add opening position: 100 shares at $10 = $1000
        t.addPosition(Transaction.fromString("01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,100,,,,10,5,-1000,Bought 100 XYZ @ 10,Individual...39"))
        
        # Close 30 shares at $12 = $360
        t.addPosition(Transaction.fromString("01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,30,,,,12,3,360,Sold 30 XYZ @ 12,Individual...39"))
        
        # Verify remaining position
        position = Transaction(t.positions.squeeze())
        assert position.getQuantity() == 70
        assert abs(position["Amount"] - (-700)) < 0.01  # 70% of original cost
        
        # Close another 40 shares at $15 = $600
        t.addPosition(Transaction.fromString("01/03/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,40,,,,15,4,600,Sold 40 XYZ @ 15,Individual...39"))
        
        # Verify final position (30 shares remain)
        position = Transaction(t.positions.squeeze())
        assert position.getQuantity() == 30
        assert abs(position["Amount"] - (-300)) < 0.01  # 30% of original cost
        
        # Verify both trades processed correctly
        assert len(t.closedTrades) == 2
        
    def test_overclosing_position(self):
        """Test what happens when trying to close more shares than exist in position"""
        t = Tasty()
        
        # Open position: 10 shares at $10 = $100
        t.addPosition(Transaction.fromString(
            "01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,10,,,,10,5,-100,Bought 10 XYZ @ 10,Individual...39"))
        
        # Try to close 20 shares (double the position size)
        with pytest.raises(ValueError, match="Tried to close a position but no previous position found"):
            t.addPosition(Transaction.fromString(
                "01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,20,,,,12,3,240,Sold 20 XYZ @ 12,Individual...39"))
